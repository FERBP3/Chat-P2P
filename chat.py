import time
import threading
import socket
import sys
import os

class Chat:

    def __init__(self,puerto_s):
        self.chateando = False
        self.esperando_aceptacion = False
        self.esperando_puerto = None
        self.conexion_cliente = None
        self.conexion_servidor = None
        self.socket_servidor = None
        self.sobrenombre_chat = "Default"
        self.sobrenombre_vecino = "DefaulNeighbor"
        self.contactos = {}
        self.puerto_s = puerto_s

    def conecta_como_cliente(self, puerto, op):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            puerto = int(puerto)
        except ValueError:
            sobrenombre = puerto
            for key, value in self.contactos.items():
                if value == sobrenombre:
                    puerto = key
                    break

        server_address = ('localhost', puerto)
        sock.connect(server_address)
        self.conexion_cliente = sock

        cadena = str(self.puerto_s) + " " + self.sobrenombre_chat
        self.conexion_cliente.sendall(cadena.encode())

        self.esperando_aceptacion = op
        if self.esperando_aceptacion:
            self.esperando_puerto = puerto

        self.chateando = True

    def espera_como_servidor(self, op):
        if op:
            self.socket_servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_address = ('localhost', self.puerto_s)
            self.socket_servidor.bind(server_address)
            self.socket_servidor.listen(1)
            print(":: Escuchando en el puerto " + str(self.puerto_s))

        self.conexion_servidor, cliente_address = self.socket_servidor.accept()

        if self.esperando_aceptacion:
            try:
                respuesta = self.conexion_servidor.recv(64).decode("utf-8")
                datos_vecino = respuesta.split(" ")
                puerto = int(datos_vecino[0])
                sobrenombre_vecino = datos_vecino[1]
                print("Checando...".format(puerto))
                print(puerto == self.esperando_puerto)
                if puerto == self.esperando_puerto:
                    esperando_aceptacion = False
                    esperando_puerto = None
                    self.contactos[puerto] = sobrenombre_vecino
                    self.sobrenombre_vecino = sobrenombre_vecino
                    print("Conexión aceptada. Ahora están conectados.")
            except:
                return

        elif not self.chateando:
            try:

                respuesta = self.conexion_servidor.recv(64).decode("utf-8")
                datos_vecino = respuesta.split(" ")
                puerto = int(datos_vecino[0])
                self.sobrenombre_vecino = datos_vecino[1]
                self.contactos[puerto] = self.sobrenombre_vecino

                print(":: Sincronizando en puerto "+ str(puerto))
                self.conecta_como_cliente(puerto, False)
            except:
                return
        self.escucha()

    def entrada(self):
        print(":: Listo para recibir comandos o mensajes")
        while True:
            comando = input()
            if comando.startswith("@sobrenombre"):
                if not self.chateando:
                    self.sobrenombre_chat = comando.split(" ")[1]
                    print(":: El sobrenombre a cambiado a "+self.sobrenombre_chat)
                else:
                    print(":: No es posible cambiar el sobrenombre durante la conversacion")

            elif comando.startswith("@contactos"):
                if not self.chateando:
                    for key, value in self.contactos.items():
                        print("{} : {}".format(value, key))
                else:
                    print(":: No es posible ver los contactos durante la conversacion")

            elif comando.startswith("@conecta"):
                if not self.chateando:
                    puerto = comando.split(" ")[1]
                    print("conectando...")
                    self.conecta_como_cliente(puerto, True)
                else:
                    print("Ya tienes un chat activo. Escribe @desconecta pata terminar al conversacion")

            elif comando.startswith("@desconecta"):
                if not self.chateando:
                    print(":: No hay ninguna conexion activa")
                    continue
                print(":: Saliste de la conversacion")
                self.chateando = False
                self.esperando_aceptacion = False
                self.esperando_puerto = None
                self.conexion_cliente.sendall(comando.encode())
                self.conexion_servidor.close()
                self.conexion_cliente.close()
                threading.Thread(target=self.espera_como_servidor, args=(False,)).start()

            elif comando.startswith("@salir"):
                print(":: Hasta la próxima")
                try:
                    self.conexion_servidor.close()
                    self.conexion_cliente.close()
                except:
                    pass
                os._exit(1)

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
                print(":: No hay conexion para leer mensajes")
                break
            if len(info) == 0:
                break
            if info.startswith("@desconecta"):
                # time.sleep(1)
                self.chateando = False
                self.esperando_aceptacion = False
                self.esperando_puerto = None
                print(":: "+self.sobrenombre_vecino + " cerro la conversacion.")
                self.conexion_cliente.close()
                self.conexion_servidor.close()
                threading.Thread(target=self.espera_como_servidor, args=(False,)).start()
                break
            elif info.startswith("@"):
                self.sobrenombre_vecino = info[1:]
                continue

            print("["+self.sobrenombre_vecino +"]"+info)

    def corre(self):
        threading.Thread(target=self.espera_como_servidor, args=(True,)).start()
        self.entrada()

Chat(int(sys.argv[1])).corre()





