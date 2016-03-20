FROM benjamincrom/dockerimage_flask_numpy_redis:latest
MAINTAINER Benjamin Crom "benjamincrom@gmail.com"
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
ENTRYPOINT ["python"]
CMD ["enrich_redis.py"]
