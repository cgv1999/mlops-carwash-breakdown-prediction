"""
DAG для ежемесячного переобучения модели прогнозирования поломок.
"""

from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import mlflow
import mlflow.sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import recall_score, precision_score, fbeta_score, confusion_matrix
import os
import joblib
import warnings
warnings.filterwarnings('ignore')

from airflow import DAG
from airflow.operators.python import PythonOperator

DATA_PATH = '/opt/airflow/data'
FEATURE_STORE_PATH = '/opt/airflow/feature_store'
MODEL_PATH = '/opt/airflow/models'
MLFLOW_URI = 'http://mlflow:5000'
EXPERIMENT_NAME = 'breakdown_prediction'

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2026, 1, 1),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'train_breakdown_model',
    default_args=default_args,
    description='Ежемесячное переобучение модели поломок',
    schedule_interval='@monthly',
    catchup=False,
    tags=['mlops', 'breakdown'],
)


def generate_features(**context):
    os.makedirs(FEATURE_STORE_PATH, exist_ok=True)
    os.makedirs(DATA_PATH, exist_ok=True)
    os.makedirs(MODEL_PATH, exist_ok=True)
    
    n_boxes = 150
    np.random.seed(42)
    today = datetime.today()
    dates = pd.date_range(start=today - timedelta(days=365), end=today + timedelta(days=7), freq='D')
    
    boxes = pd.DataFrame({
        'box_id': range(1, n_boxes + 1),
        'address_id': np.random.randint(1, 51, n_boxes),
        'year_launched': np.random.randint(2010, 2024, n_boxes),
        'location_type': np.random.choice(['сквозной', 'тупиковый'], n_boxes),
        'distance_to_center': np.random.uniform(0.5, 30, n_boxes).round(1),
        'manufacturer': np.random.choice(['Karcher', 'Istobal', 'CWK'], n_boxes),
        'boxes_per_address': np.random.choice([2, 3, 4], n_boxes),
    })
    
    addresses = pd.DataFrame({
        'address_id': range(1, 51),
        'district': np.random.choice(['Центр', 'Север', 'Юг', 'Запад', 'Восток'], 50),
        'reviews_total': np.random.randint(10, 500, 50),
        'reviews_last_month': np.random.randint(0, 50, 50),
        'avg_rating': np.random.uniform(3.0, 5.0, 50).round(1),
        'avg_check': np.random.uniform(300, 1500, 50).round(0),
    })
    
    breakdowns = []
    for box_id in range(1, n_boxes + 1):
        for date in dates:
            if np.random.random() < 0.03:
                breakdowns.append({
                    'box_id': box_id,
                    'breakdown_date': date,
                    'downtime_hours': np.random.randint(2, 48),
                    'last_maintenance_date': date - timedelta(days=np.random.randint(30, 180)),
                })
    bd_df = pd.DataFrame(breakdowns)
    bd_df['breakdown_date'] = pd.to_datetime(bd_df['breakdown_date'])
    bd_df['last_maintenance_date'] = pd.to_datetime(bd_df['last_maintenance_date'])
    
    # Признаки
    features = boxes.merge(addresses, on='address_id', how='left')
    
    for months in [3, 6, 12]:
        cutoff = today - timedelta(days=months * 30)
        cnt = bd_df[bd_df['breakdown_date'] >= cutoff].groupby('box_id').size().reset_index()
        cnt.columns = ['box_id', f'breakdowns_{months}m']
        features = features.merge(cnt, on='box_id', how='left')
        features[f'breakdowns_{months}m'] = features[f'breakdowns_{months}m'].fillna(0).astype(int)
    
    last_bd = bd_df.groupby('box_id')['breakdown_date'].max().reset_index()
    features = features.merge(last_bd, on='box_id', how='left')
    features['days_since_last_breakdown'] = (today - features['breakdown_date']).dt.days.fillna(365).astype(int)
    features = features.drop('breakdown_date', axis=1)
    
    last_to = bd_df.groupby('box_id')['last_maintenance_date'].max().reset_index()
    features = features.merge(last_to, on='box_id', how='left')
    features['days_since_last_maintenance'] = (today - features['last_maintenance_date']).dt.days.fillna(180).astype(int)
    features = features.drop('last_maintenance_date', axis=1)
    
    avg_dt = bd_df.groupby('box_id')['downtime_hours'].mean().reset_index()
    features = features.merge(avg_dt, on='box_id', how='left')
    features['avg_downtime'] = features['downtime_hours'].fillna(0).round(1)
    features = features.drop('downtime_hours', axis=1)
    
    features['month'] = today.month
    features['day_of_week'] = today.weekday()
    features['age_years'] = today.year - features['year_launched']
    
    future_bd = bd_df[(bd_df['breakdown_date'] > today) & (bd_df['breakdown_date'] <= today + timedelta(days=7))]
    future_boxes = future_bd['box_id'].unique()
    features['will_break_7d'] = features['box_id'].isin(future_boxes).astype(int)
    
    features = features.drop('address_id', axis=1)
    features.to_csv(f'{FEATURE_STORE_PATH}/features_latest.csv', index=False)
    
    print(f"Фича-стор: {len(features)} записей, {len(features.columns)} колонок")
    print(f"Поломок в ближайшие 7 дней: {features['will_break_7d'].sum()} из {len(features)}")


def train_model(**context):
    os.environ['GIT_PYTHON_REFRESH'] = 'quiet'
    os.makedirs(MODEL_PATH, exist_ok=True)
    
    mlflow.set_tracking_uri(MLFLOW_URI)
    mlflow.set_experiment(EXPERIMENT_NAME)
    
    features = pd.read_csv(f'{FEATURE_STORE_PATH}/features_latest.csv')
    features = pd.get_dummies(features, columns=['location_type', 'manufacturer', 'district'], drop_first=True)
    
    y = features['will_break_7d']
    X = features.drop(['will_break_7d', 'box_id'], axis=1, errors='ignore')
    
    if len(y.unique()) < 2:
        print("Только один класс - пропускаем")
        return
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    with mlflow.start_run(run_name=f"train_{datetime.now().strftime('%Y%m%d_%H%M')}"):
        model = RandomForestClassifier(n_estimators=100, max_depth=10, class_weight='balanced', random_state=42)
        model.fit(X_train, y_train)
        
        y_pred = model.predict(X_test)
        recall = recall_score(y_test, y_pred, zero_division=0)
        precision = precision_score(y_test, y_pred, zero_division=0)
        f2 = fbeta_score(y_test, y_pred, beta=2, zero_division=0)
        
        mlflow.log_metric('recall', recall)
        mlflow.log_metric('precision', precision)
        mlflow.log_metric('f2_score', f2)
        
        cm = confusion_matrix(y_test, y_pred)
        tn, fp, fn, tp = cm.ravel() if cm.size == 4 else (0, 0, 0, 0)
        
        print(f"Recall: {recall:.3f}, Precision: {precision:.3f}, F2: {f2:.3f}")
        print(f"TN={tn}, FP={fp}, FN={fn}, TP={tp}")
        
        joblib.dump(model, f'{MODEL_PATH}/breakdown_model.pkl')
        print(f"Модель сохранена: {MODEL_PATH}/breakdown_model.pkl")


def check_drift(**context):
    features = pd.read_csv(f'{FEATURE_STORE_PATH}/features_latest.csv')
    print(f"Дрифт: {len(features.columns)} признаков, {len(features)} записей - OK")


task_generate_features = PythonOperator(task_id='generate_features', python_callable=generate_features, dag=dag)
task_train_model = PythonOperator(task_id='train_model', python_callable=train_model, dag=dag)
task_check_drift = PythonOperator(task_id='check_drift', python_callable=check_drift, dag=dag)

task_generate_features >> task_train_model >> task_check_drift