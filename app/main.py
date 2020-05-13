from concurrent import futures
from bot_common.models.encoder_rnn import EncoderRNN
from bot_common.models.decoder_rnn import LuongAttnDecoderRNN as DecoderRNN
from bot_common.text_processing.voc import Voc
from bot_common.text_processing.utils import normalizeString
from bot_common.evaluation import GreedySearchDecoder as SearchDecoder 
from bot_common.evaluation import evaluate
from slack.signature_verification import isVerifiedSlackRequest
from slack.message_reply import reply_with

import torch
import torch.nn as nn
import logging
import grpc
import time
import os
import re
import bot_common.constants as constants
import generated.chatbot_pb2 as chatbot_pb2
import generated.chatbot_pb2_grpc as chatbot_pb2_grpc


ONE_DAY_IN_SECONDS = 60 * 60 * 24

logger = logging.getLogger(__name__)


def initializeBotsParams(model_params_file):
    logger.info('Loading model parameters...')

    params = torch.load(model_params_file, map_location=constants.DEVICE)
    encoder_state_dict = params['en']
    decoder_state_dict = params['de']
    embedding_state_dict = params['embedding']
    voc_dict = params['voc_dict']

    voc = Voc('Chatbot')
    voc.__dict__ = voc_dict

    embedding = nn.Embedding(voc.num_words, constants.HIDDEN_SIZE)
    embedding.load_state_dict(embedding_state_dict)

    encoder = EncoderRNN(embedding, constants.HIDDEN_SIZE, constants.ENCODER_GRU_LAYERS)
    decoder = DecoderRNN(
        constants.ATTN_MODEL, embedding, constants.HIDDEN_SIZE,
        voc.num_words, constants.DECODER_GRU_LAYERS
    )
    encoder.load_state_dict(encoder_state_dict)
    decoder.load_state_dict(decoder_state_dict)

    encoder.to(constants.DEVICE)
    decoder.to(constants.DEVICE)

    encoder.eval()
    decoder.eval()

    searcher = SearchDecoder(encoder, decoder, constants.DEVICE)

    return encoder, decoder, searcher, voc


class ChatbotService(chatbot_pb2_grpc.ChatbotServiceServicer):

    def __init__(self, encoder, decoder, searcher, voc):        
        self.encoder = encoder
        self.decoder = decoder
        self.searcher = searcher
        self.voc = voc
		

    def heartBeat(self, request, context):
        number = request.number
        return chatbot_pb2.HeartBeat(number=number)


    def getResponse(self, question):
        question = normalizeString(question)
        final_words = evaluate(
            self.encoder, self.decoder,
            self.searcher, self.voc, question
        )
        final_words[:] = [
            word for word in final_words \
                if not (word == 'EOS' or word == 'PAD')
        ]

        return final_words


    def chat(self, request, context):
        question = request.question
        user = request.user
        channel = request.channel
        response = []

        if question:
            response = self.getResponse(question)
            response = ' '.join(response).capitalize()
            response = re.sub(r'(\ .){2,}$', '.', response)

            if user and channel:
                response_from_slack = reply_with(response, user, channel)

                logger.info(
                    'Slack api response: {}'.format(response_from_slack.status_code)
                )
        else:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(
                'Argument(s): at least question cannot be empty string or null'
            )
            logger.error('All arguments are empty of null.')

        return chatbot_pb2.ChatbotResponse(answer=response)


def serve():
    encoder, decoder, searcher, voc = initializeBotsParams(
        os.path.join('data', 'model', 'parameters.tar')
    )

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    chatbot_pb2_grpc.add_ChatbotServiceServicer_to_server(
        ChatbotService(encoder, decoder, searcher, voc),
        server
    )

    logger.info('Starting Chatbot gRRC server...')

    server.add_insecure_port('[::]:50051')
    server.start()

    logger.info('Server started')

    try:
        while True:
            time.sleep(ONE_DAY_IN_SECONDS)
    except KeyboardInterrupt:
        logger.info('Interrupted by keyboard')
    except Exception as e:
        logger.info('Interrupted: {}'.format(e.args))
    finally:
        server.stop(0)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    serve()
