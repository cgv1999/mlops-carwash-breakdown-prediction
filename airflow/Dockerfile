FROM apache/airflow:2.6.0

RUN pip install --no-cache-dir mlflow psycopg2-binary scikit-learn pandas

USER root
RUN mkdir -p /opt/airflow/scripts && chown -R airflow /opt/airflow/scripts
USER airflow

COPY ./scripts /opt/airflow/scripts
