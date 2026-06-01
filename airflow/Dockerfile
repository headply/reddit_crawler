FROM apache/airflow:2.10.3-python3.11

USER airflow

COPY requirements.txt /opt/airflow/project/requirements.txt
RUN pip install --no-cache-dir -r /opt/airflow/project/requirements.txt

USER root
COPY . /opt/airflow/project
RUN chown -R airflow: /opt/airflow/project

USER airflow
ENV PYTHONPATH="/opt/airflow/project:${PYTHONPATH}"
