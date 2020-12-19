import time
import threading
import socket
import sys
import os

class Chat:

    def __init__(self, port):
        self.chateando = False
        self.esperando_aceptacion = False
        self.conexion_cliente = None
        self.conexion_servidor = None
        self.socket_servidor = None
        self.sobrenombre = "Default"
        self.sobrenombre_vecino = ""
        self.contactos = {}
        self.port = port
        self.address = 'localhost'
        self.client_address = 'localhost'
        self.server_conf()

    def server_conf(self):
        self.socket_servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket_servidor.bind((self.address, self.port))
        self.socket_servidor.listen(1)
        print(":: Escuchando en el puerto {}".format(str(self.port)))


    def conecta_como_cliente(self, id_conn, iniciativa):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            # id_conn es un puerto
            id_conn = int(id_conn)
        except ValueError:
            # id_conn es un sobrenombre
            for port, sobrenombre in self.contactos.items():
                if sobrenombre == id_conn:
                    id_conn = port
                    break

        sock.connect((self.client_address, id_conn))
        self.conexion_cliente = sock

        cadena = "{} {}".format(self.port, self.sobrenombre)
        self.conexion_cliente.sendall(cadena.encode())

        self.esperando_aceptacion = iniciativa

    def espera_como_servidor(self):
        try:
            self.conexion_servidor, cliente_address = self.socket_servidor.accept()
        except:
            print("La conexión del servidor fue cerrada")
            sys.exit(0)

        if self.esperando_aceptacion or not self.chateando:
            try:
                respuesta = self.conexion_servidor.recv(64).decode("utf-8")
                datos_vecino = respuesta.split(" ")
                puerto = int(datos_vecino[0])
                self.sobrenombre_vecino = datos_vecino[1]
                self.contactos[puerto] = self.sobrenombre_vecino

                if self.esperando_aceptacion:
                    self.esperando_aceptacion = False
                    print("Conexión aceptada. Ahora están conectados.")
                elif not self.chateando:
                    print(":: Sincronizando en puerto {}".format(puerto))
                    self.conecta_como_cliente(puerto, False)

            except Exception as e:
                print(e)
                return

        self.chateando = True
        print("Nueva conexión con {}".format(cliente_address))
        self.escucha()

    def entrada(self):

        print(":: Listo para recibir comandos o mensajes")
        while True:
            comando = input()

            if comando.startswith("@sobrenombre"):
                if not self.chateando:
                    self.sobrenombre = comando.split(" ")[1]
                    print(":: El sobrenombre a cambiado a "+self.sobrenombre)
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
                    puerto = comando.split(" ")[1]
                    print("conectando...")
                    self.conecta_como_cliente(puerto, True)
                else:
                    print("Ya tienes un chat activo. Escribe @desconecta pata terminar al conversación")

            elif comando.startswith("@desconecta"):
                if not self.chateando:
                    print(":: No hay ninguna conexion activa")
                    continue
                print(":: Saliste de la conversación")
                self.chateando = False
                self.esperando_aceptacion = False
                self.conexion_cliente.sendall(comando.encode())
                self.conexion_cliente.close()
                self.conexion_servidor.close()
                threading.Thread(target=self.espera_como_servidor).start()

            elif comando.startswith("@salir"):
                print(":: Hasta la próxima")
                if self.chateando:
                    self.conexion_cliente.sendall("@desconecta".encode())
                try:
                    if self.conexion_cliente is not None:
                        self.conexion_cliente.close()
                        self.conexion_servidor.close()
                    self.socket_servidor.close()
                except Exception as e:
                    print(e)
                sys.exit(0)
                break

            elif comando.startswith("@"):
                print("Comando inválido")
            else:
                try:
                    self.conexion_cliente.sendall(comando.encode())
                except:
                    print(":: No hay conexión para enviar mensajes.")

    def escucha(self):
        while True:
            info = None
            try:
                info = self.conexion_servidor.recv(64).decode("utf-8")
            except:
                print(":: No hay conexión para leer mensajes")
                break

            if len(info) == 0:
                break
            if info.startswith("@desconecta"):
                self.chateando = False
                self.esperando_aceptacion = False
                print(":: {} cerró la conversación.".format(self.sobrenombre_vecino))
                self.conexion_cliente.close()
                self.conexion_servidor.close()
                threading.Thread(target=self.espera_como_servidor).start()
                break

            print("[{}]{}".format(self.sobrenombre_vecino, info))

    def corre(self):
        threading.Thread(target=self.espera_como_servidor).start()
        self.entrada()

Chat(int(sys.argv[1])).corre()

