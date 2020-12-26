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
            connected = False
            while not connected:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.connect(('localhost', self.inter_ports[position]))
                    connected = True
                except Exception as e:
                    print("conectando...")
                    time.sleep(2)
            # Se guarda la nueva conexion
            self.inter_conn[position] = sock
            if position == 0:
                print("Se logró conectar con el cliente origen")
            else:
                print("Se logró conectar con el cliente destino")

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
                if position == 0:
                    print("Mandando mensaje al cliente origen")
                else:
                    print("Mandando mensaje al cliente destino")
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
            #print("La conexión del servidor fue cerrada")
            sys.exit(0)

        respuesta = new_client.recv(1024).decode("utf-8")
        try:
            print("Se recibió: {}".format(respuesta))
            if self.chateando or self.is_bridge:
                respuesta = respuesta.split(" ")
                print("Se intentó conectar alguien mientras estabas chateando")
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect(('localhost', int(respuesta[1])))
                mensaje = "@occupied"
                sock.sendall(mensaje.encode())
                return
            if respuesta.startswith('@occupied'):
                print("El cliente está ocupado")
                threading.Thread(target=self.espera_como_servidor).start()
                return

            if self.server_conn[0] is None:
                self.server_conn[0] = new_client
            else:
                self.server_conn[1] = new_client

            if respuesta.startswith('@puente'):
                respuesta = respuesta.split(" ")

                self.inter_ports[0] = int(respuesta[2])
                self.inter_ports[1] = int(respuesta[3])
                self.inter_sobrenombres[0] = respuesta[1]
                self.inter_sobrenombres[1] = self.contactos[self.inter_ports[1]]

                mensaje = "@intermediario {} {}".format(self.addr[1], self.inter_sobrenombres[0])
                self.conecta_como_cliente(None, mensaje, True, 1)
                self.espera_como_servidor()

                print("mandando @accept al origen")
                mensaje = "@accept_puente {} ".format(self.addr[1])
                self.conecta_como_cliente(None, mensaje, True, 0)

                self.is_bridge = True
                threading.Thread(target=self.escucha, args=(self.server_conn[0], self.inter_conn[1], self.inter_sobrenombres[0],)).start()
                threading.Thread(target=self.escucha, args=(self.server_conn[1], self.inter_conn[0], self.inter_sobrenombres[1],)).start()
                return

            elif respuesta.startswith('@accept_puente'):
                respuesta = respuesta.split(" ")

                self.client_addr[1] = int(respuesta[1])

            elif respuesta.startswith('@intermediario'):
                respuesta = respuesta.split(" ")

                self.client_addr[1] = int(respuesta[1])
                self.sobrenombre_vecino = respuesta[2]
                print(":: Sincronizando en puerto de intermediario {}".format(self.client_addr[1]))
                mensaje = "@accept_inter"
                self.conecta_como_cliente(self.client_addr[1], mensaje, False, None)
            elif respuesta.startswith('@accept_inter'):
                return

            elif respuesta.startswith('@request') or respuesta.startswith('@accept'):
                respuesta = respuesta.split(" ", 3)

                self.client_addr[1] = int(respuesta[1])
                self.sobrenombre_vecino = respuesta[2]
                self.contactos[self.client_addr[1]] = str(self.sobrenombre_vecino)
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
                self.chateando = False
                self.esperando_aceptacion = False
                try:
                    self.client_conn.sendall(comando.encode())
                    self.client_conn.close()
                    self.server_conn[0].close()
                except Exception as e:
                    print("error en desconecta", e)

                self.server_conn[0] = None
                self.server_conn[1] = None
                self.inter_conn[0] = None
                self.inter_conn[1] = None
                self.client_addr[1] = None
                self.client_conn = None
                self.sobrenombre_vecino = ""
                self.contactos_vecino = {}

                print(":: Saliste de la conversación")
                threading.Thread(target=self.espera_como_servidor).start()

            elif comando.startswith("@salir"):
                try:
                    if self.is_bridge:
                        self.inter_conn[0].sendall("@desconecta".encode())
                        self.inter_conn[1].sendall("@desconecta".encode())

                    if self.chateando:
                        self.client_conn.sendall("@desconecta".encode())
                    if self.client_conn is not None:
                        self.client_conn.close()
                        self.server_conn[0].close()
                    self.socket_servidor.close()
                except Exception as e:
                    print("error al salir: ", e)
                print(":: Hasta la próxima")
                sys.exit(0)
                break

            elif comando.startswith("@"):
                print("Comando inválido")
            else:
                if not self.chateando:
                    print("No tienes una conversación abierta")
                else:
                    try:
                        self.client_conn.sendall(comando.encode())
                    except Exception as e:
                        print("error en sendall")

    def escucha(self, origin, dest, sobrenombre_origin):
        while True:
            info = None
            try:
                info = origin.recv(64).decode("utf-8")
            except Exception as e:
                print("Excepcion :escucha_como_servidor ", e)
                break

            print("Se recibió: ", info)
            if len(info) == 0:
                if self.is_bridge:
                    print("error : no hay datos por leer de uno de los cliente")
                else:
                    print("Hubo un error en la conexión buscando intermediario...")
                    try:
                        self.client_conn.close()
                        self.server_conn[0].close()
                    except Exception as e:
                        print("excepcion cerrando conexiones ", e)

                    self.client_conn = None
                    self.server_conn[0] = None

                    self.chateando = False
                    self.esperando_aceptacion = True

                    bridge_port = self.get_bridge_port()
                    if bridge_port is None:
                        print("El vecino no tiene contactos para usar como intermediario, cerrando conexiones...")
                        try:
                            self.server_conn[0].close()
                            if self.is_bridge:
                                self.server_conn[1].close()
                                self.inter_conn[0].close()
                                self.inter_conn[1].close()
                            else:
                                self.client_conn.close()
                        except Exception as e:
                            print("error al cerrar conns en escucha: ", e)

                        print(":: {} cerró la conversación.".format(self.sobrenombre_vecino))
                        self.server_conn[0] = None
                        self.server_conn[1] = None
                        self.inter_conn[0] = None
                        self.inter_conn[1] = None
                        self.client_addr[1] = None
                        self.client_conn = None
                        self.sobrenombre_vecino = ""
                        self.chateando = False
                        self.esperando_aceptacion = False
                        self.is_bridge = False
                        self.contactos_vecino = {}

                        threading.Thread(target=self.espera_como_servidor).start()
                        break

                    print("puerto escogido como intermediario: ", bridge_port)
                    mensaje = "@puente {} {} {}".format(self.sobrenombre, self.addr[1], self.client_addr[1])
                    self.conecta_como_cliente(bridge_port, mensaje, False, None)
                    threading.Thread(target=self.espera_como_servidor).start()
                break

            if info.startswith("@desconecta"):
                if self.is_bridge:
                    dest.sendall("@desconecta".encode())

                try:
                    self.server_conn[0].close()
                    if self.is_bridge:
                        self.server_conn[1].close()
                        self.inter_conn[0].close()
                        self.inter_conn[1].close()
                    else:
                        self.client_conn.close()
                except Exception as e:
                    print("error al cerrar conns en escucha: ", e)

                print(":: {} cerró la conversación.".format(self.sobrenombre_vecino))
                self.server_conn[0] = None
                self.server_conn[1] = None
                self.inter_conn[0] = None
                self.inter_conn[1] = None
                self.client_addr[1] = None
                self.client_conn = None
                self.sobrenombre_vecino = ""
                self.chateando = False
                self.esperando_aceptacion = False
                self.is_bridge = False
                self.contactos_vecino = {}

                threading.Thread(target=self.espera_como_servidor).start()
                break

            print("[{}]{}".format(sobrenombre_origin, info))
            if self.is_bridge:
                dest.sendall(info.encode())

    def get_bridge_port(self):
        if len(self.contactos_vecino) == 0:
            return None
        return choice(list(self.contactos_vecino.keys()))

    def corre(self):
        threading.Thread(target=self.espera_como_servidor).start()
        self.entrada()

Chat(int(sys.argv[1])).corre()

