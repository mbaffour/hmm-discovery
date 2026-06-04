FROM mambaorg/micromamba:1.5.10

WORKDIR /app
COPY --chown=$MAMBA_USER:$MAMBA_USER environment.yml requirements.txt /app/
RUN micromamba install -y -n base -f /app/environment.yml && micromamba clean -a -y

COPY --chown=$MAMBA_USER:$MAMBA_USER . /app
EXPOSE 8081

ENV PYTHONUNBUFFERED=1
CMD ["micromamba", "run", "-n", "base", "python", "-m", "shiny", "run", "app.py", "--host", "0.0.0.0", "--port", "8081"]
