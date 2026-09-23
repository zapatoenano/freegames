FROM python:3.11-slim
WORKDIR /app
COPY . /app
WORKDIR /app/free-games-api
RUN python -m pip install --no-cache-dir -r requirements.txt
EXPOSE 8000
ENV FREEGAMES_TTL=300
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
