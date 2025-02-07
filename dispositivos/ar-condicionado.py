import grpc
from concurrent import futures
import arquivos_pb2.servicos_dispositivos_pb2 as response_request
import arquivos_pb2.servicos_dispositivos_pb2_grpc as services

#variáveis
ip_gateway=""
porta_gateway=0
ip_broker=""
porta_broker=0
ip="localhost"
porta=0

_id="ar-condicionado00"
estado="desligado"
temperatura=24
temperatura_ambiente=24



class ArCondicionadoService(services.ArCondicionadoServiceServicer):
    
    def LigarDesligar(self, request, context):
        global estado
        if estado=="desligado":
            estado="ligado"
        else:
            estado="desligado"    
        return response_request.StatusResponse(status=f"Estado alterado para {estado}")
    
    def Temperatura(self, request, context):
        global temperatura 
        temperatura = request.temperaturaEscolhida
        return response_request.StatusResponse(status=f"Temperatura alterada para {temperatura}")

    
def serve():
    global porta
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    services.add_ArCondicionadoServiceServicer_to_server(ArCondicionadoService(), server)
    port_bind = server.add_insecure_port('[::]:0')
    porta = port_bind
    server.start()
    print(f"Servidor {_id} rodando na porta {porta}...")
    server.wait_for_termination()
if __name__ == '__main__':
    serve()