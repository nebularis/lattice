FROM python:3.14-slim
COPY wheelhouse /wheels
RUN pip install --no-index --find-links /wheels pika rdflib \
 && pip install --no-index --no-deps --find-links /wheels lattice-workers
USER 10001
ENTRYPOINT ["python", "-m", "lattice_workers.wording_analysis_main"]
