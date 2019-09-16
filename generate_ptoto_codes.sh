if [ -d "./app/generated" ]
then
	rm -rf ./app/generated/*
else
	mkdir -p ./app/generated
fi

python3 -m grpc_tools.protoc -I./protos --python_out=./app/generated --grpc_python_out=./app/generated ./protos/chatbot.proto

touch ./app/generated/__init__.py
