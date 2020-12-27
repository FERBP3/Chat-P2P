import time
import threading
import socket
import sys
import os
import json
from random import choice

class Chat:

    def __init__(self, port):
        self.socket_servidor = None
        self.client_conn = None
        self.server_conn = [None, None]
        self.inter_conn = [None, None]
        self.inter_ports = [None, None]
        self.inter_sobrenombres = ["", ""]
        self.chateando = False
        self.esperando_aceptacion = False
        self.is_bridge = False
        self.sobrenombre = "Default"
        self.sobrenombre_vecino = ""
        self.contactos = {}
        self.contactos_vecino = {}
        self.addr = ['localhost', port]
        self.client_addr = ['localhost', None]
        self.server_conf()

    def server_conf(self):
        self.socket_servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket_servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket_servidor.bind((self.addr[0], self.addr[1]))
        self.socket_servidor.listen(1)
        print(":: Escuchando en el puerto {}".format(str(self.addr[1])))

    def conecta_como_cliente(self, id_conn, mensaje, puente, position):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Se converte el id_conn en un puerto válido
        # Si es puente, los puertos ya están en self.inter_ports
        if not puente:
            try:
                # id_conn es un puerto
                id_conn = int(id_conn)
            except ValueError:
                # id_conn es un sobrenombre
                for port, sobrenombre in self.contactos.items():
                    if sobrenombre == id_conn:
                        id_conn = port
                        break
            self.client_addr[1] = id_conn

        # Se conecta con uno o dos cliente dependiendo si funciona como puente (intermediario)
        if puente:
            # Se trata de conectar al cliente de formar persistente
            while sock.connect_ex(('localhost', self.inter_ports[position])) != 0:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                print("conectando con el cliente...")
                time.sleep(2)

            # Se guarda la nueva conexion
            self.inter_conn[position] = sock
        else:
            try:
                sock.connect(('localhost', self.client_addr[1]))
                self.client_conn = sock
            except Exception as e:
                print("El usuario no está disponible")
                return

        # Se le manda el mensaje al cliente
        try:
            if puente:
                self.inter_conn[position].sendall(mensaje.encode())
            else:
                self.client_conn.sendall(mensaje.encode())
        except Exception as e:
            if puente:
                if position == 0:
                    print("Error mandando mensaje al cliente origen")
                else:
                    print("Error mandando mensaje al cliente destino")
            else:
                print("Error al enviar mensaje al cliente")

    def espera_como_servidor(self):
        try:
            new_client, _ = self.socket_servidor.accept()
        except:
            sys.exit(0)

        respuesta = new_client.recv(1024).decode("utf-8")
        try:
            #print("Se recibió: {}".format(respuesta))
            if self.server_conn[0] is None:
                self.server_conn[0] = new_client
            else:
                self.server_conn[1] = new_client

            respuesta = respuesta.split(" ", 3)
            if respuesta[0] == '@inter_accepted':
                return
            if respuesta[0] == '@puente':
                print("Solicitud de servidor recibida")

                self.inter_ports[0] = int(respuesta[2])
                self.inter_ports[1] = int(respuesta[3])
                self.inter_sobrenombres[0] = respuesta[1]
                self.inter_sobrenombres[1] = self.contactos[self.inter_ports[1]]

                mensaje = "@intermediario {} {}".format(self.addr[1], self.inter_sobrenombres[0])
                self.conecta_como_cliente(None, mensaje, True, 1)
                self.espera_como_servidor()

                mensaje = "@puente_accepted {} {}".format(self.addr[1], self.inter_sobrenombres[1])
                self.conecta_como_cliente(None, mensaje, True, 0)

                print("Solicitud de servidor aceptada. Ahora soy un servidor")
                self.is_bridge = True
                threading.Thread(target=self.escucha, args=(self.server_conn[0], self.inter_conn[1], self.inter_sobrenombres[0],)).start()
                threading.Thread(target=self.escucha, args=(self.server_conn[1], self.inter_conn[0], self.inter_sobrenombres[1],)).start()
                return

            else:
                self.client_addr[1] = int(respuesta[1])
                self.sobrenombre_vecino = respuesta[2]
                if respuesta[0] == '@puente_accepted':
                    pass
                elif respuesta[0] == '@intermediario':
                    print(":: Sincronizando en puerto de intermediario {}".format(self.client_addr[1]))
                    mensaje = "@inter_accepted"
                    self.conecta_como_cliente(self.client_addr[1], mensaje, False, None)

                elif respuesta[0] == '@request' or respuesta[0] == '@accept':
                    self.contactos[self.client_addr[1]] = self.sobrenombre_vecino
                    self.contactos_vecino = json.loads(respuesta[3])

                    if self.contactos_vecino.get(str(self.addr[1]), None) is not None:
                        del self.contactos_vecino[str(self.addr[1])]

                    if self.esperando_aceptacion:
                        print("Conexión aceptada. Ahora están conectados.")
                    elif not self.chateando:
                        print(":: Sincronizando en puerto {}".format(self.client_addr[1]))
                        mensaje = "@accept {} {} {}".format(self.addr[1], self.sobrenombre, json.dumps(self.contactos))
                        self.conecta_como_cliente(self.client_addr[1], mensaje, False, None)
        except Exception as e:
            print(e)
            return

        self.chateando = True
        self.esperando_aceptacion = False
        print("Nueva conexión con {}".format(self.client_addr))
        self.escucha(self.server_conn[0], None, self.sobrenombre_vecino)

    def entrada(self):

        print(":: Listo para recibir comandos o mensajes")
        while True:
            comando = input()
            if comando.startswith("@sb"):
                if not self.chateando:
                    self.sobrenombre = comando.split(" ")[1]
                    print(":: El sobrenombre a cambiado a {}".format(self.sobrenombre))
                else:
                    print(":: No es posible cambiar el sobrenombre durante la conversación")

            elif comando.startswith("@contactos"):
                if not self.chateando:
                    for key, value in self.contactos.items():
                        print("{} : {}".format(value, key))
                else:
                    print(":: No es posible ver los contactos durante la conversación")
            elif comando.startswith("@conecta"):
                if not self.chateando:
                    id_conn = comando.split(" ")[1]
                    print("conectando...")
                    mensaje = "@request {} {} {}".format(self.addr[1], self.sobrenombre, json.dumps(self.contactos))
                    self.esperando_aceptacion = True
                    self.conecta_como_cliente(id_conn, mensaje, False, None)
                else:
                    print("Ya tienes un chat activo. Escribe @desconecta pata terminar al conversación")

            elif comando.startswith("@desconecta"):
                if not self.chateando:
                    print(":: No hay ninguna conexion activa")
                    continue
                message = ":: Saliste de la conversación"
                self.restart_conections(message)

            elif comando.startswith("@salir"):
                self.close_conections(True)
                break

            elif comando.startswith("@"):
                print("Comando inválido")
            else:
                if not self.chateando:
                    print("No tienes una conversación abierta")
                elif self.esperando_aceptacion:
                    print("Espera a que te respondan")
                else:
                        self.client_conn.sendall(comando.encode())

    def close_conections(self, exit):
        #Primero avisamos a nuestros clientes y luego desconectamos todo
        try:
            if self.is_bridge:
                self.inter_conn[0].sendall("@desconecta".encode())
                self.inter_conn[1].sendall("@desconecta".encode())
                self.inter_conn[0].close()
                self.inter_conn[1].close()
                self.server_conn[0].close()
                self.server_conn[1].close()

            else:
                if self.chateando:
                    self.client_conn.sendall("@desconecta".encode())
                    self.client_conn.close()
                    self.server_conn[0].close()
                else:
                    if self.client_conn is not None and self.server_conn[0] is not None:
                        self.client_conn.close()
                        self.server_conn[0].close()
        except Exception as e:
            print("error en desconecta", e)

        if exit:
            self.socket_servidor.close()
            sys.exit(0)

        self.server_conn = [None, None]
        self.inter_conn = [None, None]
        self.inter_ports = [None, None]
        self.inter_sobrenombres = ["",""]
        self.client_addr[1] = None
        self.client_conn = None
        self.sobrenombre_vecino = ""
        self.contactos_vecino = {}
        self.is_bridge = False
        self.chateando = False
        self.esperando_aceptacion = False

    def escucha(self, origin, dest, sobrenombre_origin):
        while True:
            info = None
            try:
                info = origin.recv(64).decode("utf-8")
            except Exception as e:
                break

            #print("Se recibió: ", info)
            if len(info) == 0:
                if self.is_bridge:
                    print("error : no hay datos por leer de uno de los clientes")
                    dest.sendall("@desconecta".encode())
                    message = ":: {} cerró la conversación.".format(self.sobrenombre_vecino)
                    self.restart_conections(message)
                    break

                else:
                    print("Hubo un error en la conexión buscando intermediario...")
                    bridge_port = self.get_bridge_port()
                    if bridge_port is None:
                        message = "El vecino no tiene contactos para usar como intermediario, cerrando conexiones..."
                        self.restart_conections(message)
                        break

                    mensaje = "@puente {} {} {}".format(self.sobrenombre, self.addr[1], self.client_addr[1])
                    # Se guardan los atributos que no se tienen que borrar
                    sobrenombre_vecino = self.sobrenombre_vecino
                    contactos_vecino = self.contactos_vecino
                    self.close_conections(False)

                    self.esperando_aceptacion = True
                    self.sobrenombre_vecino = sobrenombre_vecino
                    self.contactos_vecino = contactos_vecino

                    print("puerto escogido como intermediario: ", bridge_port)
                    self.conecta_como_cliente(bridge_port, mensaje, False, None)
                    threading.Thread(target=self.espera_como_servidor).start()
                break

            if info.startswith("@desconecta"):
                if self.is_bridge:
                    dest.sendall("@desconecta".encode())
                message = ":: {} cerró la conversación.".format(self.sobrenombre_vecino)
                self.restart_conections(message)
                break

            print("[{}]{}".format(sobrenombre_origin, info))
            if self.is_bridge:
                dest.sendall(info.encode())

    def get_bridge_port(self):
        if len(self.contactos_vecino) == 0:
            return None
        return choice(list(self.contactos_vecino.keys()))

    def restart_conections(self, message):
        print(message)
        self.close_conections(False)
        threading.Thread(target=self.espera_como_servidor).start()

    def corre(self):
        threading.Thread(target=self.espera_como_servidor).start()
        self.entrada()

Chat(int(sys.argv[1])).corre()

