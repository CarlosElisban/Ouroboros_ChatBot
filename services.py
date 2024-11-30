import requests
import sett
import json
import time
import base64
from Crypto.Cipher import AES

#Lista que tendra los mensajes del usuario, para descifrar y cifrar
listaValsCypher = []
listaValsUncypher = []

class Ajustador:
    @staticmethod
    def ajustar_key(key, longitud=16):
        """
        Ajusta la longitud de la clave a la especificada (16 bytes por defecto).
        Si es más corta, se rellena; si es más larga, se trunca.
        """
        key_bytes = key.encode('utf-8')  # Convertimos a bytes si no lo está
        if len(key_bytes) < longitud:
            # Rellenamos con bytes nulos (\0)
            key_bytes += b'\0' * (longitud - len(key_bytes))
        elif len(key_bytes) > longitud:
            # Truncamos a la longitud especificada
            key_bytes = key_bytes[:longitud]
        return key_bytes

class CifradoCesar:
    # Permite definir atributos como el desplazamiento y los caracteres que existen en la tabla B64 (No estan ordenados)
    def __init__(self, desplazamiento=5):
        self.charB64 = "sOrTzf3WDM2pP/6tceoy9b07GCna8SVxZv4gYhwXUk1BjEN5RIu+=HFqAiJQdKmlL"
        self.desplazamiento = desplazamiento
    
    # Para que esta función pueda cifrar, utiliza la función de desplazamiento por cada caracter del texto 
    def cifrar(self, texto: str) -> str:
        
        texto_cifrado = ''.join([self._desplazar_caracter(caracter) for caracter in texto])
        
        return texto_cifrado

    # Para que esta función pueda descifrar, utiliza la función de desplazamiento por cada caracter del texto_cifrado 
    # Con un desplazamiento de -5
    def descifrar(self, texto_cifrado: str) -> str:
      
        texto_descifrado = ''.join([self._desplazar_caracter(caracter, -self.desplazamiento) for caracter in texto_cifrado])
        
        return texto_descifrado 
    
    
    def _desplazar_caracter(self, caracter: str, valor_desplazamiento=None) -> str:
        if valor_desplazamiento is None:
            valor_desplazamiento = self.desplazamiento
        if caracter in self.charB64:
            # Suma la posición donde se ubica el caracter con el desplazamiento 
            # Al utilizar % es para que la ubicación sea ciclica, ejem 63 + 5 = 68 
            # 68%64 = 4, por lo tanto el nuevo caracter se encuentra en la posicion 4
            idx = (self.charB64.index(caracter) + valor_desplazamiento) % len(self.charB64)
            return self.charB64[idx] #Retorna el caracter que se encuentra dentro de esa posició
        else:
            return caracter

class AESEncrypt:
  
    @staticmethod
    def encryptAES(key, data):
        cipher = AES.new(key, AES.MODE_EAX)
        ciphertext, tag = cipher.encrypt_and_digest(data)

        return cipher.nonce + tag + ciphertext
      
    @staticmethod
    def decryptAES(key, data):
        nonce = data[:AES.block_size]
        tag = data[AES.block_size:AES.block_size * 2]
        ciphertext = data[AES.block_size * 2:]

        cipher = AES.new(key, AES.MODE_EAX, nonce)

        return cipher.decrypt_and_verify(ciphertext, tag)

def obtener_Mensaje_whatsapp(message):
    
    #Si el tipo de mensaje no esta definido 
    if 'type' not in message :
        text = 'mensaje no reconocido'
        return text

    #Se toma el tipo de mensaje
    typeMessage = message['type']
    
    #Cuando la respuesta del usuario es texto
    if typeMessage == 'text':
        text = message['text']['body']
        
    #Cuando la respuesta del usuario proviene de la seleccion de una opcion del boton
    elif typeMessage == 'interactive' and message['interactive']['type'] == 'button_reply':
        text = message['interactive']['button_reply']['title']
    
    # El mensaje no es de ningun tipo, no procesa
    else:
        text = 'mensaje no procesado'

    return text
  
'''
Envia todos los mensaje que ya estan en formato de Whatsapp, utiliza el token y la url generado por Meta, para que sea posible
enviar el mensaje al numero correspondiente
'''
def enviar_Mensaje_whatsapp(data):
    try:
      # El token y la URL se generan en la Configuración de la API y adjunta en el archivo sett.py
        whatsapp_token = sett.whatsapp_token
        whatsapp_url = sett.whatsapp_url
        
        #Se utiliza el token, para realizar un encabezado HTTP
        headers = {'Content-Type': 'application/json',
                   'Authorization': 'Bearer ' + whatsapp_token}
        
        #Se envia una solicitud POST a la API, que contiene el header y la data, para que este tome una decisión
        response = requests.post(whatsapp_url, 
                                 headers=headers,
                                 data=data)
        
        #Si la la API permitión realizar la acción su respuesta sera 200, sino sera error
        
        if response.status_code == 200:
            return 'mensaje enviado', 200
        else:
            return 'error al enviar mensaje', response.status_code
    except Exception as e:
        return e,403
'''
Sus parametros son el numero del usuario y el texto con el cual se quiere responder, para colocarlo en un formato adecuado
para Whatsapp, no utiliza, botones, footer. Solo numero y texto
'''
def text_Message(number,text):
    data = json.dumps(
            {
                "messaging_product": "whatsapp",    
                "recipient_type": "individual",
                "to": number, #numero del usuario
                "type": "text",
                "text": {
                    "body": text #Respuesta del chatbot
                }
            }
    )
    return data

'''

Esta función a traves de la respuesta del usuario
realiza la parte de cifrar el texto y elaborar una respuesta adecuada para Whatsapp, solo se necesita
el numero de mensaje recibido
'''
def text_Message_cifrado(number):
    try:
        # Se crea un objeto en base a la clase AESEncrypt con el fin de hacer uso a sus funciones
        AESc = AESEncrypt()
        # Se crea un objeto en base a la clase CifradoCesar con el fin de hacer uso a sus funciones
        cesar = CifradoCesar()
        # Se crea un objeto en base a la clase Ajustador con el fin de hacer uso a sus funciones
        ajus = Ajustador()
      
        # listaValsCypher = ["Texto: JuanPerez", "Clave: 123"]  
        # listaValsCypher[0] = ["Texto: JuanPerez"]     
        # partes_texto_cifrado = ["","JuanPerez"]       Lo mismo con la otra lista, el 1 indica que
        # solo se partirá hasta encontrar solo la primera coincidencia, si se aumenta 1 mas, se parte mas veces

        partes_texto_a_cifrar = listaValsCypher[0].split("Texto:",1)
        partes_clave_a_cifrar = listaValsCypher[1].split("Clave:",1)

        #partes_texto_cifrado[1] = ["", "    J uan Perez  "] - ejemplo
        #text = "JuanPerez"
        text = partes_texto_a_cifrar[1].lstrip() #elimina los espacios en blanco del valor de la posicion 1
        key = partes_clave_a_cifrar[1].lstrip()
        #Se convierte el texto en plano en bytes- ejemplo b'JuanPerez
        textb = text.encode('utf-8')
        #Se envia el la clave a la funcion ajustar_key, con el objetivo de retornar un valor en bytes que sea igual a 16 bytes
        keyb = ajus.ajustar_key(key)
        #Se convierte la clave ajustada en bytes a hexadecimal - Proposito: enviar al usuario
        key_hex = keyb.hex()
        
        # Se envia la clave ajustada y el texto en bytes, para cifrarlo con AES - Salida: bytes
        cifrado_AES = AESc.encryptAES(keyb, textb)
        
        # Se utiliza B64, para convertirlo en caracteres textuales
        cifradoAES_B64 = base64.b64encode(cifrado_AES).decode('utf-8')
        
        # Se utiliza los caracteres textuales generados y se utiliza cifrado cesar
        CifradoFinal = cesar.cifrar(cifradoAES_B64)
        #Se envia una respuesta, ahi se debe adjuntar tanto el cifrado final como la clave en hexadecimal
        data = json.dumps(
                {
                    "messaging_product": "whatsapp",    
                    "recipient_type": "individual",
                    "to": number, #numero del usuario
                    "type": "text",
                    "text": {
                        "body": f"*¡Aquí tienes tu texto cifrado!* 🎉 {CifradoFinal}\n *Y esta es tu nueva clave* 🔑:  {key_hex}\n*¡Guárdala en un lugar seguro!* 😊" #texto cifrado
                    }
                }
            )
        return data
        
    except Exception as e:
        print("listavals------",listaValsCypher[0])
        print("listavals.......",listaValsCypher[1])
        print("Error en text_Message_cifrado:", e)
        #Se imprime el error
        return f"Error: {e}"
      
'''

Esta función a traves de la respuesta del usuario
realiza la parte de descifrar el texto y elaborar una respuesta adecuada para Whatsapp, solo se necesita
el numero de mensaje recibido

'''

def text_Message_descifrado(number):
    try:
        # Se crea un objeto en base a la clase AESEncrypt con el fin de hacer uso a sus funciones
        AESc = AESEncrypt()
        # Se crea un objeto en base a la clase CifradoCesar con el fin de hacer uso a sus funciones
        cesar = CifradoCesar()
        # Se crea un objeto en base a la clase Ajustador con el fin de hacer uso a sus funciones
        ajus = Ajustador()
        
        # listaValsUncypher = ["Texcif: 70td9Itq6tR/cvFuJ6elDSwApO2+wkWNw6d23LnKYaTwfwO9LOEi", "Clavecif: 62616e64626164626667383437373834"]  
        # listaValsCypher[0] = ["Texcif: 70td9Itq6tR/cvFuJ6elDSwApO2+wkWNw6d23LnKYaTwfwO9LOEi"]     
        # partes_texto_cifrado = ["","70td9Itq6tR/cvFuJ6elDSwApO2+wkWNw6d23LnKYaTwfwO9LOEi"], el 1 indica que
        # solo se partirá hasta encontrar solo la primera coincidencia, si se aumenta 1 mas, se parte mas veces
        partes_texto_cifrado = listaValsUncypher[0].split("Texcif:",1)
        partes_clave_cifrado = listaValsUncypher[1].split("Clavecif:",1)
        
        #partes_texto_cifrado[1] = ["", "7 0t d9 I tq6t R/c vFu J6e   lD SwApO2+wkWNw6d23LnKYaTwfwO 9LOEi "]
        #text = "70td9Itq6tR/cvFuJ6elDSwApO2+wkWNw6d23LnKYaTwfwO9LOEi"
        text = partes_texto_cifrado[1].lstrip() #elimina los espacios en blanco del valor de la posicion 1
        key = partes_clave_cifrado[1].lstrip()
        
        #Se envia el texto para desencriptar por medio de cesar
        cifradoAES_B64 = cesar.descifrar(text)
        
        #Convierte un valor textual en bytes - ejemplo b' valor
        cifradoAES = base64.b64decode(cifradoAES_B64)
        
        #Convierte los valores hexadecimales de la clave en bytes - ejemplo b' 62616e64626164626667383437373834 
        keybytes = bytes.fromhex(key)
        
        #Se utiliza la clave y el resultado del CifradoAES en formato bytes para desencriptarlos
        descifrado_AES = AESc.decryptAES(keybytes,cifradoAES)
        
        #Se convierte el valor descifrado de byte a texto 
        descifrado_AESTexto = descifrado_AES.decode('utf-8')

        #Se envia el texto desencriptado - Se elabora un mensaje en formato adecuado y se adjunta el texto desencriptado
        data = json.dumps(
            {
                "messaging_product": "whatsapp",    
                "recipient_type": "individual",
                "to": number, #numero del usuario
                "type": "text",
                "text": {
                    "body": f"*¡Aquí tienes tu texto descifrado!* 🎉, espero que sea justo lo que buscabas: {descifrado_AESTexto}"
                }
            }
        )
        return data
    except Exception as e:

        partes_texto_cifrado = listaValsUncypher[0].split("des_text:",1)
        partes_clave_cifrado = listaValsUncypher[1].split("des_key:",1)

        text = partes_texto_cifrado[1].lstrip()
        key = partes_clave_cifrado[1].lstrip()

        print("listavals------",text)
        print("listavals.......",key)
        print("Error en text_Message_cifrado:", e)
        #Se imprime el error
        return f"Error: {e}"

'''

Esta función permite elaborar respuestas más elaboradas ya que en sus parametros tiene opciones, un footer y 
sedd que añade IDs a cada boton.

'''
def buttonReply_Message(number, options, body, footer, sedd):
  
  # Se transforma las opciones en botones Reply = un boton
    buttons = []
    for i, option in enumerate(options):
        buttons.append(
            {
                "type": "reply",
                "reply": {
                    "id": sedd + "_btn_" + str(i+1),
                    "title": option
                }
            }
        )
        
# Se elabora el mensaje de respuesta en formato adecuado para whatsapp, este incluye el numero del usuario, el footer y los botones
    data = json.dumps(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": number,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {
                    "text": body #Hola 🤝, soy tu ayudante en cifrado y descifrado. ¿Qué puedo hacer ahora por ti?
                },
                "footer": {
                    "text": footer #Aqui por ejemplo va "Ouroboros"
                },
                "action": {
                    "buttons": buttons #Aqui iria los botones
                }
            }
        }
    )
    return data
  
'''
Esta función requiere de un numero de telefono, el ID del mensaje y un emoji respectivo, esto con el proposito de
Reaccionar mediante el emoji respectivo al mensaje que coincida con el numero y el ID.
Retorna un formato de texto  adecuado para Whatsapp

'''
def replyReaction_Message(number, messageId, emoji):
    data = json.dumps(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": number, #El numero del usuario
            "type": "reaction",
            "reaction": {
                "message_id": messageId, #El id del mensaje del usuario
                "emoji": emoji #El emoji que se va a reaccional al mensaje del usuario
            }
        }
    )
    return data

'''
  Esta función permite que cuando segun sea ID que este en su parametro, se marque que se ha visto el mensaje que tenga ese ID.
  En este caso se utilizo para dejar un visto a todos los mensajes del usuario.
  Retorna un formato de texto adecuado para Whatsapp.

'''
def markRead_Message(messageId):
    data = json.dumps(
        {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id":  messageId #El id del mensaje del usuario
        }
    )
    return data

'''
Esta función permite gestionar las respuestas del chatbot, según sea los mensajes del usuario

El chatbot gestiona lo siguiente:

- Cifrar: Le pide el texto que se requiere cifrar y la clave (Esta sera crucial para descifrar) - retorna el texto cifrado 
  con una clave cifrada.
- Descrifrar: Le pide el texto que se ha cifrado y la clave que el usuario establecio durante la etapa del cifrado - retorna
  el texto descifrado
'''
def administrar_chatbot(text,number, messageId, name):
  
    # Esta lista permite adjunta los mensajes que se van generando  
    list = []
    # Se imprime en consola el mensaje del usuario
    print("mensaje del usuario: ",text)
    
    
    #Se toma el ID del mensaje del usuario y se utiliza la función markRead_Message, el resultado se adjunta a la lista
    
    markRead = markRead_Message(messageId)
    
    #Se marca que fue visto el mensaje
    list.append(markRead)
    
    #Controlamos el ritmo de ejecución, pausando 1 segundos
    time.sleep(1)
    
    #Esta condicional solo sera cuando el mensaje del usuario comience: "hola" o variantes, "hi" o variantes
    
    if "hola" in text.lower() or "hi" in text.lower():
        
        #Cadena de mensaje
        answer = "Hola 🤝, soy tu ayudante en cifrado y descifrado. ¿Qué puedo hacer ahora por ti?"
        
        # lo que va abajo del mensaje
        footer = "Ouroboros"
        
        # Botones de selección
        opciones = ["Cifrar un mensaje", "Descifrar un mensaje"]
        
        # Se usa la función buttonReply_Message, permite enviar un mensaje que pueda acoplar botones de selección y un footer
        # Mensaje interactivo
        replyButtonData = buttonReply_Message(number, opciones, answer, footer, "sed1")
        
        # Se usa la función replyReaction_Message, permite que se pueda reaccionar al mensaje que envio el usuario
        replyReaction = replyReaction_Message(number, messageId, "👋")
        
        # Se adjunta ambos mensajes a la lista
        list.append(replyReaction)
        list.append(replyButtonData)
        
    elif "Si, por favor" in text:
        
        #Cadena de mensaje
        answer = "Hola 🤝, nuevamente. ¿Qué puedo hacer ahora por ti?"
        
        # lo que va abajo del mensaje
        footer = "Ouroboros"
        
        # Botones de selección
        opciones = ["Cifrar un mensaje", "Descifrar un mensaje"]
        
        # Se usa la función buttonReply_Message, permite enviar un mensaje que pueda acoplar botones de selección y un footer
        # Mensaje interactivo
        replyButtonData = buttonReply_Message(number, opciones, answer, footer, "sed11")
        
        # Se usa la función replyReaction_Message, permite que se pueda reaccionar al mensaje que envio el usuario
        replyReaction = replyReaction_Message(number, messageId, "😉")
        
        # Se adjunta ambos mensajes a la lista
        list.append(replyReaction)
        list.append(replyButtonData)
    
    #Esta condicional solo sera cuando el mensaje del usuario comience: "Cifrar..." o seleccione el boton que diga " 🔒 Cifrar"

    elif "Cifrar un mensaje" in text:
       
        # Mensaje simple
        aswer1 = text_Message(number, "¡Perfecto! 😊 Escribe el texto que quieres cifrar y estaré listo para ayudarte. \nSolo escríbelo así: \n*Texto: <Aquí el mensaje que necesitas cifrar>*")
        
        list.append(aswer1)
        
    #Esta condicional solo sera cuando el mensaje del usuario comience: "Texto: ..."

    elif "Texto:" in text:
       
        # Se crea un respuesta y se le transforma en un formato simple y adecuado
        answer2 = text_Message(number,"¡Excelente!, 👏🎉 todo listo, hemos recibido tu texto")
        
        # Se obtiene el mensaje del usuario "Texto: ...., y se adjunta a la lista listaValsCypher "
        texto_cifrar = text
        listaValsCypher.append(texto_cifrar)

        # Se crea un segunda respuesta y se le transforma en un formato simple y adecuado
        answer3 = text_Message(number,"Ahora escribe la clave para cifrar tu texto. \nDe esta manera: \n*Clave: <Aquí escribe la clave textualmente>*")

        # Se añade ambas respuestas a la lista
        list.append(answer2)
        list.append(answer3)
    
    #Esta condicional solo sera cuando el mensaje del usuario comience: "Clave: ..."

    elif "Clave:" in text:
       
        # Se crea un respuesta y se le transforma en un formato simple y adecuado
        answer4 = text_Message(number,"¡Super! hemos recibido tu clave.  Dame un momento, estamos haciendo el proceso de cifrado 🔒.")
        
        # Se obtiene el mensaje del usuario "Clave: ...., y se adjunta a la lista listaValsCypher
        clave_cifrar = text
        listaValsCypher.append(clave_cifrar)

        # Se crea respuestas y se le transforma en un formato simple y adecuado
        answer5 = text_Message(number,"⏳⏳⏳⏳⏳⏳")
        answer6 = text_Message(number,"⏳⏳⏳⏳⏳⏳⏳")
        answer7 = text_Message(number,"⏳⏳⏳⏳⏳⏳⏳⏳")
        
        # Se toma la respuestas que este relacionado con cifrar el texto y la clave
        mensaje = text_Message_cifrado(number)
        
        
        answer8 = "¿Necesitas algo más? Estoy aquí para ayudarte. 💬"
        
        # lo que va abajo del mensaje
        footer = "Ouroboros"
        
        # Botones de selección
        opciones = ["Si, por favor"]
        
        # Se crea una respuesta interactiva para que responda el chatbot
        answer8_1 = buttonReply_Message(number, opciones, answer8, footer, "sed10")
        
        #Se adjunta todos los mensajes a la lista
        list.append(answer4) 
        list.append(answer5)
        list.append(answer6)
        list.append(answer7)
        list.append(mensaje)
        list.append(answer8_1)
        
        #Se limpia la lista
        listaValsCypher.clear()
          
    #Esta condicional solo sera cuando el mensaje del usuario comience: "Descifrado..." o seleccione el boton que diga "🔓 Descifrado"

    elif "Descifrar un mensaje" in text:
        
        # Se crea una respuesta simple
        
        aswer9 = text_Message(number, "¡Perfecto! 😊 Escribe el texto cifrado que quieres descifrar y estaré listo para ayudarte. \nSolo escríbelo así: \n*Texcif: <Aquí el mensaje que necesitas cifrar>*")
        
        list.append(aswer9)
    
    #Esta condicional solo sera cuando el mensaje del usuario comience: "Texcif: ..."
    
    elif "Texcif:" in text:
       
        # Se crea un respuesta y se le transforma en un formato simple y adecuado
        answer10 = text_Message(number,"¡Excelente!, 👏🎉 todo en orden, hemos anotado tu texto cifrado")
        
        # Se obtiene el mensaje del usuario "Texcif: ...., y se adjunta a la lista listaValsUncypher
        texto_descifrar = text
        listaValsUncypher.append(texto_descifrar)
        time.sleep(3)

        # Se crea una segunda respuesta y se le transforma en un formato simple y adecuado
        answer11 = text_Message(number,"Ahora escribe tu clave cifrada que se te fue entregada. \nDe esta manera: \n*Clavecif: <Aquí escribe tu clave cifrada>*")

        #Se añaden ambas respuestas a la lista
        list.append(answer10)
        list.append(answer11)
    
    #Esta condicional solo sera cuando el mensaje del usuario comience: "Clavecif: ..."

    elif "Clavecif:" in text:
       
        # Se crea un respuesta y se le transforma en un formato simple y adecuado
        answer12 = text_Message(number,"¡Super! hemos recibido tu clave cifrada. Dame un momento, estamos haciendo el proceso de descifrado 🔓.")
        
        # Se obtiene el mensaje del usuario "Clave: ...., y se adjunta a la lista listaValsCypher
        clave_descifrar = text
        listaValsUncypher.append(clave_descifrar)
        time.sleep(3)
        
        # Se crea respuestas y se le transforma en un formato simple y adecuado
        answer13 = text_Message(number,"⏳⏳⏳⏳⏳⏳")
        answer14 = text_Message(number,"⏳⏳⏳⏳⏳⏳⏳")
        answer15 = text_Message(number,"⏳⏳⏳⏳⏳⏳⏳⏳")
        
        # Se obtiene el texto descifrado
        answer16 = text_Message_descifrado(number)
        
        answer17 = "¿Necesitas algo más? Estoy aquí para ayudarte. 💬"
        
        # lo que va abajo del mensaje
        footer = "Ouroboros"
        
        # Botones de selección
        opciones = ["Si, por favor"]
        
        # Se realiza una respuesta interactiva
        answer17_1 = buttonReply_Message(number, opciones, answer17, footer, "sed20")
        
        # Se añaden todas las respuestas y se adjunta  a la lista
        list.append(answer12)
        list.append(answer13)
        list.append(answer14)
        list.append(answer15)
        list.append(answer16)
        list.append(answer17_1)
        listaValsUncypher.clear()
    
    #Esta condicional solo sera cuando el mensaje del usuario comience no cumple con ninguna condicional 
    else :
      
        # Se crea una tercera respuesta y se le transforma en un formato simple y adecuado
        data = text_Message(number,"Disculpa, no entendí bien lo que dijiste 🤔. ¿Te importa repetirlo? 😊")
        
        # Se adjunta  la respuesta a la lista
        list.append(data)
    
    # Se toma todas las respuestas añadidas en cada posicion distinta en la lista
    for item in list:
        time.sleep(2)
        # Se envia el mensaje
        enviar_Mensaje_whatsapp(item)