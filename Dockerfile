FROM pytorch/pytorch

ARG HOST_SLACK_SIGNING_SECRET
ARG HOST_BOT_USER_OAUTH_ACCESS_TOKEN

ENV SLACK_SIGNING_SECRET=$HOST_SLACK_SIGNING_SECRET
ENV BOT_USER_OAUTH_ACCESS_TOKEN=$HOST_BOT_USER_OAUTH_ACCESS_TOKEN

EXPOSE 50051

COPY ./app/generated /app/generated
COPY ./app/slack /app/slack
COPY ./app/main.py /app/main.py
COPY ./app/data /app/data
COPY ./app/requirements.txt /app/requirements.txt

WORKDIR /app/

RUN pip install -r requirements.txt

# Run the start script, it will check for an /app/prestart.sh script (e.g. for migrations)
# And then will start Gunicorn with Uvicorn
CMD ["python", "main.py"]
