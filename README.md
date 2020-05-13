# Chatbot Service

A chatbot service developed by using Grpc and PyTorch that receive a slack chat message from an edging servcie [chatbot-receiver](https://github.com/callibrity/chatbot-receiver) as protocal buffer, and then reply the chat message to the slack channel where the message is from.

To run the service locally, you have to have `Python3 (>=3.6)` and `PyTorch` installed, you can refer to `PyTorch` official website on how to install for your platform.

Other dependances can be installed using `pip` with the `requirements.txt` located within `app` directory.

```
pip install -r requirements.txt
``` 

Once all dependances are installed, you can run
```
python (or python3) main.py
```

The grpc service will be exposed on port `50051`.
