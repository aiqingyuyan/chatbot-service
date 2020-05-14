FROM pytorch/pytorch

ENV SLACK_SIGNING_SECRET=
ENV BOT_USER_OAUTH_ACCESS_TOKEN=

EXPOSE 50051

COPY ./app/generated /app/generated
COPY ./app/slack /app/slack
COPY ./app/main.py /app/main.py
COPY ./app/data /app/data
COPY ./app/requirements.txt /app/requirements.txt

WORKDIR /app/

RUN pip install -r requirements.txt

CMD ["python", "main.py"]
