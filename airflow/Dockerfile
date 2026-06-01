FROM apache/airflow:2.10.3-python3.11

USER root

COPY requirements.txt /opt/airflow/project/requirements.txt
RUN pip install --no-cache-dir -r /opt/airflow/project/requirements.txt

COPY . /opt/airflow/project
ENV PYTHONPATH="/opt/airflow/project:${PYTHONPATH}"

USER airflow
