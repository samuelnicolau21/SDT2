import grpc
from concurrent import futures
import arquivos_pb2.servicos_dispositivos_pb2 as response_request
import arquivos_pb2.servicos_dispositivos_pb2_grpc as services

# Variáveis globais
ip_gateway = ""
porta_gateway = 0
ip_broker = ""
porta_broker = 0
ip = "192.168.1.5"
porta = 0

_id = "lampada00"
estado = "desligado"
brilho = 50
luminosidade = 50



class LampadaService(services.LampadaServiceServicer):

    def LigarDesligar(self, request, context):
        global estado
        estado = "ligado" if estado == "desligado" else "desligado"
        return response_request.StatusResponse(status=f"Estado alterado para {estado}")

    def Brilho(self, request, context):
        global brilho
        brilho = request.brilho
        return response_request.StatusResponse(status=f"Brilho alterado para {brilho}")

def serve():
    global porta
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    services.add_LampadaServiceServicer_to_server(LampadaService(), server)
    port_bind = server.add_insecure_port('[::]:0')
    porta = port_bind
    server.start()
    print(f"Servidor {_id} rodando na porta {porta}...")
    server.wait_for_termination()


if __name__ == '__main__':
    serve()
