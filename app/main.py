import unicodedata
import re
import pickle
import torch
import logging
import grpc
import time
import generated.chatbot_pb2 as chatbot_pb2
import generated.chatbot_pb2_grpc as chatbot_pb2_grpc
from concurrent import futures
from common.text_utils import normalizeString, MAX_LENGTH
from common.model import EncoderRNN, AttnDecoderRNN, device
from common.lang import SOS_Token, EOS_Token, UNK_Token, Lang
from slack.signature_verification import isVerifiedSlackRequest
from slack.message_reply import reply_with


logger = logging.getLogger(__name__)

hidden_size = 256
ONE_DAY_IN_SECONDS = 60 * 60 * 24


def readLangsData():
    with open('langs/questions.pkl', 'rb') as q_in, open('langs/answers.pkl', 'rb') as a_in:
        q_data = pickle.load(q_in)
        a_data = pickle.load(a_in)

    question_lang, answer_lang = Lang('question'), Lang('answer')

    question_lang.fromPickle(q_data)
    answer_lang.fromPickle(a_data)
    
    return (question_lang, answer_lang)


def indexesFromSentence(lang, sentence):
    return [
        lang.word2index[word] if word in lang.word2index else UNK_Token
        for word in sentence.split(' ')
    ]


def tensorFromSentence(lang, sentence):
    indexes = indexesFromSentence(lang, sentence)
    indexes.append(EOS_Token)
    return torch.tensor(indexes, dtype=torch.long, device=device).view(-1, 1)


def evaluate(encoder, decoder, question_lang, answer_lang, sentence, max_length=MAX_LENGTH):
    with torch.no_grad():
        input_tensor = tensorFromSentence(question_lang, sentence)
        input_length = input_tensor.size(0)
        
        encoder_hidden = encoder.initHidden()
        encoder_outputs = torch.zeros(max_length, encoder.hidden_size, device=device)
        
        for ei in range(input_length):
            encoder_output, encoder_hidden = encoder(input_tensor[ei], encoder_hidden)
            encoder_outputs[ei] += encoder_output[0, 0]

        decoder_input = torch.tensor([[SOS_Token]], device=device)
        
        decoder_hidden = encoder_hidden
        
        decoded_words = []
        
        for di in range(max_length):
            decoder_output, decoder_hidden, decoder_attention = decoder(
                decoder_input,
                decoder_hidden,
                encoder_outputs
            )
            topv, topi = decoder_output.topk(1)

            if topi.item() == EOS_Token:
                break
            else:
                decoded_words.append(answer_lang.index2word[topi.item()])
					
            decoder_input = topi.squeeze().detach()
        
        return decoded_words


def initializeBotsParams():
    question_lang, answer_lang = readLangsData()

    encoder = EncoderRNN(question_lang.num_of_words, hidden_size).to(device)
    decoder = AttnDecoderRNN(hidden_size, answer_lang.num_of_words, dropout_p=0.1).to(device)

    location = 'cpu' if device.type == 'cpu' else None

    encoder.load_state_dict(torch.load('model/encoder.pt', map_location=location))
    decoder.load_state_dict(torch.load('model/decoder.pt', map_location=location))

    encoder.eval()
    decoder.eval()

    if location == 'cpu':
        logger.info('Running model on CPU')
    else:
        logger.info('Running model on CUDA/GPU')

    return question_lang, answer_lang, encoder, decoder


class ChatbotService(chatbot_pb2_grpc.ChatbotServiceServicer):

    def __init__(self):
        question_lang, answer_lang, encoder, decoder = \
            initializeBotsParams()
        
        self.question_lang = question_lang
        self.answer_lang = answer_lang
        self.encoder = encoder
        self.decoder = decoder
		

    def heartBeat(self, request, context):
        number = request.number
        return chatbot_pb2.HeartBeat(number=number)


    def getResponse(self, question):
        question = normalizeString(question)
        response = evaluate(
            self.encoder,
            self.decoder,
            self.question_lang,
            self.answer_lang,
            question
        )
        return response


    def chat(self, request, context):
        question = request.question
        user = request.user
        channel = request.channel
        response = []

        if question:
            response = self.getResponse(question)

            logger.info('Pre enter...')

            if user and channel:
                logger.info('Enter, pre-send...')
                response_from_slack = reply_with(response, user, channel)
                logger.info('Enter, after-send...')

                logger.info(
                    'Slack api response: {}'.format(response_from_slack.status_code)
                )
        else:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(
                'Argument(s): at least question cannot be empty string or null'
            )
            logger.error('All arguments are empty of null.')

        return chatbot_pb2.ChatbotResponse(answer=' '.join(response).capitalize())


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    chatbot_pb2_grpc.add_ChatbotServiceServicer_to_server(
        ChatbotService(),
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
