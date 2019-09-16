FROM pytorch/pytorch

RUN pip install grpcio-tools
RUN pip install common-aiqingyuyan

ARG HOST_SLACK_SIGNING_SECRET
ARG HOST_BOT_USER_OAUTH_ACCESS_TOKEN

ENV SLACK_SIGNING_SECRET=$HOST_SLACK_SIGNING_SECRET
ENV BOT_USER_OAUTH_ACCESS_TOKEN=$HOST_BOT_USER_OAUTH_ACCESS_TOKEN

EXPOSE 50051

COPY ./app/generated /app/generated
COPY ./app/langs /app/langs
COPY ./app/model /app/model
COPY ./app/slack /app/slack
COPY ./app/main.py /app/main.py

WORKDIR /app/

# Run the start script, it will check for an /app/prestart.sh script (e.g. for migrations)
# And then will start Gunicorn with Uvicorn
CMD ["python", "main.py"]
