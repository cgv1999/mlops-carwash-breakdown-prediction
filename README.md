# MLOps Level 2: Система предиктивного обслуживания автомоек "NDA"

**Учебный проект по дисциплине "Развертывание ML-моделей"**

---

## Содержание

1. [О проекте]
2. [Как развернуть систему]
3. [Доказательство работы]
4. [Выполнение критериев]
5. [Архитектура]
6. [Документация]
7. [Структура репозитория]

---

## О проекте

Система предсказывает, какой моечный бокс на автомойке выйдет из строя в ближайшие 7 дней. 
Это позволяет перейти от реактивного ремонта (когда уже сломалось) к профилактическому обслуживанию.

**Заказчик:** федеральная сеть автомоек "NDA" - 50 адресов, 150 моечных боксов.

**Бизнес-цель:** снизить время простоя боксов с 10% до 5% рабочего времени.

**ML-цель:** бинарная классификация (сломается / не сломается) с приоритетом Recall ≥ 80% (пропустить поломку дороже, чем ложный выезд механика).

**Заявленный уровень зрелости: 2.**

---

## Как развернуть систему

### Требования

- Docker Desktop
- 8+ ГБ свободной оперативной памяти

### Шаг 1: Клонировать репозиторий

```bash
git clone https://github.com/cgv1999/mlops-carwash-breakdown-prediction.git
cd mlops-carwash-breakdown-prediction
```

### Шаг 2: Запустить все сервисы

```bash
docker-compose up -d
```

Подождать 30-40 секунд (скачиваются образы, запускаются базы данных).

### Шаг 3: Проверить, что все работает

```bash
docker-compose ps
```

Ожидаемый результат - 8 сервисов в статусе Up (некоторые с пометкой healthy):

https://docs/docker_ps.png

### Шаг 4: Запустить ML-пайплайн (обучение модели)

```bash
docker-compose exec airflow airflow dags unpause train_breakdown_model
docker-compose exec airflow airflow dags trigger train_breakdown_model
```

После выполнения (около минуты) в папке feature_store/ появится файл features_latest.csv, в папке airflow/models/ - breakdown_model.pkl.

### Шаг 5: Проверить API

```bash
curl http://localhost:8001/health
curl http://localhost:8001/predict/box/1
```

### Шаг 6: Открыть веб-интерфейсы

Airflow	(http://localhost:8080): оркестрация ML-пайплайна

MLflow (http://localhost:5000):	трекинг экспериментов и реестр моделей

FastAPI	(http://localhost:8001/docs): интерактивная документация API

Prometheus (http://localhost:9090): сбор метрик

Grafana	(http://localhost:3000): дашборды мониторинга

Логины и пароли: Airflow - admin / admin, Grafana - admin / admin.

### Доказательство работы:

https://docs/docker_ps.png

На скриншоте видно: postgres (healthy), airflow-db (healthy), api (healthy), mlflow, airflow, prometheus, grafana, node-exporter.

1. API отвечает на health check:

```bash
curl http://localhost:8001/health
```

2. MLflow доступен:

```bash
curl http://localhost:5000
```

3. Grafana показывает дашборд:

https://grafana/dashboards/dashboard.png

4. Prometheus собирает метрики с Node Exporter:

```bash
curl http://localhost:9090/api/v1/targets
```

5. Airflow DAG выполняется успешно:

```bash
docker-compose exec airflow airflow dags list
```

6. MDD-анализ: сравнение latency:

https://docs/latency_comparison.png

Статистический тест показал: t = 1875.08, p-value ≈ 0.000000.

Улучшенная система статистически значимо быстрее (на 42.9%).

### Выполнение критериев:

**Критерий 1: Постановка цели (2/2)**

Бизнес-метрика: время простоя боксов (снизить с 10% до 5%).

ML-метрики (в порядке приоритета):

- Recall ≥ 80% - пропустить поломку дороже, чем ложный выезд
- Precision ≥ 60% - чтобы механики не игнорировали предупреждения
- F2-score ≥ 0.7 - компромисс с приоритетом Recall

Почему не Accuracy: классы несбалансированы (поломки редки). 
Модель, всегда говорящая "не сломается", даст 95% accuracy при нулевой пользе.

Подробнее: ML-манифест, разделы 1-3.

**Критерий 2: Уровень зрелости ML-системы (2/2)**

Заявлен уровень 2. Система включает все обязательные компоненты:

- Версионирование кода: Git + GitHub

- CI/CD пайплайн: GitHub Actions (.github/workflows/ci.yml)

- Фича-стор: feature_store/features_latest.csv (заполняется Airflow DAG)

- Сервинг модели через API: FastAPI (/predict/box/{id}, /predict/address/{id})

- Мониторинг качества: Prometheus + Grafana + Node Exporter

- Система управления экспериментами: MLflow (Tracking Server + Model Registry)

- Оркестратор: Airflow (DAG train_breakdown_model)

Полный жизненный цикл модели:

- Данные генерируются - признаки сохраняются в фича-стор

- Airflow DAG ежемесячно обучает модель

- Метрики логируются в MLflow

- Если Recall ≥ 60% - модель принимается, иначе остается в Staging

- API загружает модель из MLflow Registry (Production) или из локального файла

- При падении Recall ниже порога запускается внеплановое переобучение

Подробнее: ML-манифест, раздел 4.

**Критерий 3: Создание ML-системы (1/2)**

Что сделано:

- Код на GitHub: https://github.com/cgv1999/mlops-carwash-breakdown-prediction

- Инфраструктура как код: docker-compose.yml (8 сервисов)

- Все компоненты работают - скриншот docker ps приложен выше

- Эндпоинт /health отвечает 200 (см. скриншот выше)

- CI/CD пайплайн проверяет сборку и здоровье всех сервисов

**Критерий 4: Управление рисками (2/2)**

Документ: docs/sli_slo.md - 8 метрик на трех уровнях.

Технический уровень (4 метрики):

- Доступность MLflow (Docker healthcheck)
- Доступность API (Docker healthcheck)
- Загрузка CPU (Prometheus + Node Exporter)
- Использование RAM (Prometheus + Node Exporter)

Модельный уровень (3 метрики):

- Recall (расчет в Airflow DAG при каждом обучении)
- Precision (расчет в Airflow DAG)
- Количество пропущенных поломок (Confusion Matrix в DAG)

Бизнес-уровень (1 метрика):

- Время простоя боксов (данные ERP, в учебном проекте - синтетические)

Для каждой метрики указан SLO (целевое значение) и критический порог.

**Критерий 5: MDD и ADR (2/2)**

Выполнен полный цикл Metrics Driven Development:

- Сгенерированы два набора данных: существующая система (μ=3.5 сек) и улучшенная (μ=2.0 сек), по 500 000 наблюдений
- Построена визуализация распределений

Сформулированы гипотезы:

H0: среднее время отклика одинаковое

H1: улучшенная система быстрее

Выбран уровень значимости α = 0.05

Проведен двусторонний t-тест для независимых выборок

Результат: t = 1875.08, p-value ≈ 0.000000

Вывод: H0 отклоняется, улучшенная система статистически значимо быстрее на 42.9%

Результат оформлен как ADR: docs/adr_latency.md с разделами Context, Hypotheses, Method, Decision, Consequences.

Код анализа: scripts/mdd_analysis.py

Архитектура:

```text
┌─────────────────────────────────────────────────────────────┐
│                      Docker Compose                         │
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐   │
│  │ Postgres │  │  MLflow  │  │ Airflow  │  │  FastAPI   │   │
│  │ (MLflow  │  │ Tracking │  │   DAG    │  │  /predict  │   │
│  │ + AF DB) │  │ Registry │  │          │  │  /health   │   │
│  └──────────┘  └──────────┘  └──────────┘  └────────────┘   │
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐   │
│  │Prometheus│  │ Grafana  │  │  Node    │  │  Feature   │   │
│  │  :9090   │  │  :3000   │  │ Exporter │  │   Store    │   │
│  └──────────┘  └──────────┘  └──────────┘  └────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

Поток данных:

- Airflow DAG генерирует синтетические данные - сохраняет в data/

- DAG считает признаки - сохраняет в feature_store/features_latest.csv

- DAG обучает Random Forest - сохраняет модель в airflow/models/

- FastAPI читает модель и признаки - отдает прогнозы

- MLflow логирует параметры, метрики и артефакты

- Prometheus собирает системные метрики - Grafana отображает дашборды

Документация:

- docs/MANIFEST.md: ML-манифест: 12 разделов постановки задачи

- docs/sli_slo.md: индикаторы надежности на 3 уровнях

- docs/adr_latency.md: архитектурное решение по latency (MDD)

Структура репозитория:

```text
mlops-carwash-breakdown-prediction/
│
├── .github/workflows/ci.yml  # CI/CD пайплайн (GitHub Actions)
├── docker-compose.yml  # Инфраструктура как код (8 сервисов)
│
├── airflow/  # Оркестратор ML-пайплайна
│   ├── Dockerfile
│   ├── dags/train_pipeline.py  # DAG: генерация данных - фичи - обучение
│   └── scripts/entrypoint.sh  # Скрипт запуска Airflow
│
├── api/  # Сервинг модели
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app.py  # FastAPI: /health, /predict/box/{id}
│
├── mlflow/  # Сервер MLflow
│   └── Dockerfile
│
├── prometheus/  # Конфигурация сбора метрик
│   └── prometheus.yml
│
├── grafana/  # Дашборды мониторинга
│   ├── datasources.yml
│   ├── dashboards.yml
│   └── dashboards/
│       ├── dashboard.png  # Скриншот дашборда
│       └── node-exporter.json  # Конфигурация дашборда
│
├── docs/  # Документация
│   ├── MANIFEST.md  # ML-манифест
│   ├── sli_slo.md  # SLI/SLO
│   ├── adr_latency.md  # ADR по MDD
│   ├── latency_comparison.png  # Визуализация распределений
│   └── docker_ps.png  # Скриншот работающих сервисов
│
├── feature_store/  # Хранилище признаков
│   └── features_latest.csv  # Актуальные признаки (генерируется DAG)
│
├── scripts/  # Вспомогательные скрипты
│   ├── generate_data.py  # Генератор синтетических данных
│   └── mdd_analysis.py  # MDD-анализ (t-тест, визуализация)
│
├── data/  # Сырые данные (генерируются DAG)
│   ├── boxes.csv
│   ├── addresses.csv
│   └── breakdowns.csv
│
├── README.md  # Этот файл
└── .gitignore
```
