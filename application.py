import requests
import os
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

ACCESS_TOKEN = os.getenv("WA_TOKEN")
PHONE_NUMBER_ID = "766952236510382"
URL = f"https://graph.facebook.com/v22.0/{PHONE_NUMBER_ID}/messages"

verify_token = "montokenwoyofal"
sessions = {}
TIMEOUT_MINUTES = 5


application = Flask(__name__)

#Tarifs TTC par tranche (en FCFA/kWh)
TRANCHES_DPP = [
    {"name": "tranche 1", "max": 150, "prix": 93.45},
    {"name": "tranche 2", "max": 250, "prix": 139.90},
    {"name": "tranche 3", "max": float('inf'), "prix": 165.08}
]
TRANCHES_DMP = [
    {"name": "tranche 1", "max": 150, "prix": 114.015},
    {"name": "tranche 2", "max": 250, "prix": 147.13},
    {"name": "tranche 3", "max": float('inf'), "prix": 173.61}
]
TRANCHES_PPP = [
    {"name": "tranche 1", "max": 150, "prix": 167.90},
    {"name": "tranche 2", "max": 250, "prix": 194.59},
    {"name": "tranche 3", "max": float('inf'), "prix": 229.61}
]
TRANCHES_PMP = [
    {"name": "tranche 1", "max": 150, "prix": 169.14},
    {"name": "tranche 2", "max": 250, "prix": 195.79},
    {"name": "tranche 3", "max": float('inf'), "prix": 231.03}
]

FRAIS_LOCATION = 429  # Frais à la première recharge du mois

def montant_vers_kwh(cumul_montant, tranches):
    cumul_kwh = 0
    montant_restant = cumul_montant
    for tranche in tranches:
        tranche_limit = tranche['max']
        tranche_prix = tranche['prix']
        quota_kwh = tranche_limit - cumul_kwh
        cout_tranche = quota_kwh * tranche_prix

        if montant_restant >= cout_tranche:
            cumul_kwh += quota_kwh
            montant_restant -= cout_tranche
        else:
            kwh_possible = montant_restant / tranche_prix
            cumul_kwh += kwh_possible
            break
    return cumul_kwh


def calcul_kwh(puissance, montant, cumul_montant, is_premiere_recharge):
    detail_tranches=[]

    if is_premiere_recharge:
        montant -= FRAIS_LOCATION
    else :
        cumul_montant -= FRAIS_LOCATION
    if puissance == "dpp":
        tranches = TRANCHES_DPP
    elif puissance == "dmp":
        tranches = TRANCHES_DMP
    elif puissance == "ppp":
        tranches = TRANCHES_PPP
    elif puissance == "pmp":
        tranches = TRANCHES_PMP
    else :
        return 0
    cumul_kwh = montant_vers_kwh(cumul_montant, tranches)
    total_kwh = 0
    montant_restant = montant
    cumul_temp = cumul_kwh    
    for tranche in tranches:
        tranche_name=tranche['name']
        tranche_limit = tranche['max']
        tranche_prix = tranche['prix']
        if cumul_temp >= tranche_limit:
            continue   # déjà consommé cette tranche
        quota_tranche = tranche_limit - cumul_temp
        cout_tranche = quota_tranche * tranche_prix

        if montant_restant >= cout_tranche:
            detail_tranches.append({'name':tranche_name,'prix': tranche_prix, 'kwh': quota_tranche})
            total_kwh += quota_tranche
            montant_restant -= cout_tranche
            cumul_temp += quota_tranche
        else:            
            kwh_tranche = montant_restant / tranche_prix
            total_kwh += kwh_tranche   
            detail_tranches.append({'name':tranche_name,'prix': tranche_prix, 'kwh': kwh_tranche})
            montant_restant = 0
            break     
    location = 0
    if is_premiere_recharge :
        location = FRAIS_LOCATION

    return {"kwh":round(total_kwh, 1),
            "detail_tranches":detail_tranches
            }
def format_montant(valeur):
        return f"{int(valeur):,}".replace(",", " ")

def generer_detail_recharge(montant_total, detail_tranches, frais_location):
    lignes = [f"🔍 *Détail de votre recharge de {format_montant(montant_total)} FCFA* :\n"]
    montant_utilise = 0
    total_kwh = 0

    if frais_location:
        lignes.append(f"• 📦 *Frais de location compteur* -> *{int(FRAIS_LOCATION):,} FCFA*")
        montant_utilise += FRAIS_LOCATION

    for tranche in detail_tranches:
        name=tranche['name']
        kwh = round(tranche['kwh'], 2)
        prix = round(tranche['prix'], 2)
        cout = round(kwh * prix, 0)
        montant_utilise += cout
        total_kwh += kwh

        lignes.append(
            f"• *{name}* -> *{round(kwh, 1)}* kWh -> *{format_montant(cout)} FCFA*"
        )

    lignes.append(f"\n📊 *Total énergie : {round(total_kwh, 1)} kWh*")
    '''lignes.append(f"💵 *Montant total utilisé : {int(montant_utilise):,} F*")'''

    return "\n".join(lignes)

def format_indented_block(text, indent="   ", max_length=50):
    words = text.split()
    lines = []
    current_line = indent
    for word in words:
        if len(current_line) + len(word) + 1 > max_length:
            lines.append(current_line)
            current_line = indent + word
        else:
            current_line += " " + word
    lines.append(current_line)
    return "\n".join(lines)


@application.route('/calc', methods=['POST'])
def calc():
    data = request.get_json()

    montant = float(data.get('montant'))  # montant à recharger
    cumul_recharge = float(data.get('cumul_recharge'))  # total déjà rechargé ce mois
    is_premiere_recharge = data.get('is_premiere_recharge', False)

    kwh = calcul_kwh(montant, cumul_recharge, is_premiere_recharge)

    return jsonify({
        "kwh_estime": kwh
    })
'''if __name__ == '__main__':
    application.run(debug=True)'''



'''@application.route("/", methods=["GET"])
def home():
    return "Bot WhatsApp en ligne !"
if __name__ == '__main__':
    application.run(debug=True)'''

@application.route('/webhook', methods=['GET'])
def verify():
    verify_token = "montokenwoyofal"
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.verify_token") == verify_token:
        return request.args.get("hub.challenge"), 200
    return "Erreur de vérification du token", 403


@application.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    try:
        message = data["entry"][0]["changes"][0]["value"]["messages"][0]
        sender = message["from"]
        if 'text' in message:
            text = message['text']['body']
        elif 'interactive' in message:
            text = message['interactive']['button_reply']['title']
        else:
            text = ""
            
        manageTIMEOUTSession(sender)

        if text.lower() in ["restart", "recommencer"]:
            sessions[sender] = {"step": 1}
            send_button_message(sender, "On recommence. Quelle est votre type d'installation ?", ["Domestique", "Professionnel"])

        # Logique par étapes
        if sender not in sessions:
            sessions[sender] = {'step': 1}
            bloc_puissances = format_indented_block("a. DPP pour Domestique Petite Puissance (puissance la plus fréquente) \n" \
            "b. DMP pour Domestique Moyenne Puissance \n\n" \
            "c. PPP pour Professionnel Petite Puissance \n" \
            "d. PMP pour Professionnel Moyenne Puissance")
            send_message(sender, "Bienvenue sur Xam Sa Woyofal 👋. \n\n" \
            "Ce service a pour but de vous aider à estimer le nombre de kwh que vous allez recevoir après votre recharge.\n" \
            "Afin de pouvoir vous aider, nous allons avoir besoin de quelques informations :\n\n" \
            "1. Le type d'installation : Domestique ou Professionnel \n" \
            "2. La puissance souscrite : Petite Puissance (DPP ou PPP) ou Moyenne Puissance (DMP ou PMP)\n" \
            "3. S'agit-il de votre première recharge du mois. Si oui on passe directement à l'étape 5 \n\n" \
            "4. S'il ne s'agit pas de votre première recharge, le montant total déjà rechargé dans le mois (par exemple 15.000 si vous aviez déjà rechargé 10.000 et 5.000 FCFA plutôt dans le mois) \n\n" \
            "5. Enfin le montant que vous souhaitez recharger \n\n\n\n" \
            "A tout moment vous pouvez revenir au tout début en répondant 'Recommencer'")

            send_button_message(sender, "Quelle est votre type d'installation ?", ["Domestique", "Professionnel"])

            '''options = [("DPP", "DPP"),
                       ("DMP", "DMP"),
                       ("PPP", "PPP"),
                       ("PMP", "PMP")]

            send_list_message(to=sender,
                              header_text="Choix de la puissance",
                              body_text="Sélectionne ta puissance souscrite :",
                              footer_text="Woyofal Helper",
                              button_text="Choisir",
                              section_title="Types de puissances",
                              options=options)'''

            # Mise à jour du timestamp
            sessions[sender]['last_active'] = datetime.now()
        
        elif sessions[sender]['step']==1:
            sessions[sender]['last_active'] = datetime.now()
            sessions[sender]['type']=text.lower()
            if not text.lower() in ['domestique', 'professionnel']:
                send_message(sender, f"Votre installation Woyofal est soit domestique soit professionnelle")
                send_button_message(sender, "Quelle est votre type d'installation ?", ["Domestique", "Professionnel"])
            else:
                sessions[sender]['step'] = 2
                if text.lower()=='domestique':
                    send_button_message(sender, "Quelle est votre puissance souscrite ?", ["DPP", "DMP", "Recommencer"])
                else : 
                    send_button_message(sender, "Quelle est votre puissance souscrite ?", ["PPP", "PMP", "Recommencer"])

        elif sessions[sender]['step'] == 2:
            # Mise à jour du timestamp
            sessions[sender]['last_active'] = datetime.now()
            sessions[sender]['puissance'] = text.lower()
            if sessions[sender]['type']=='domestique' and not text.lower() in ["dpp", "dmp"]:
                send_message(sender, f"La valeur choisie n'est pas une puissance valide")
                send_button_message(sender, "Quelle est votre puissance souscrite ?", ["DPP", "DMP", "Recommencer"])
            elif sessions[sender]['type']=='professionel' and not text.lower() in ["ppp", "pmp"]: 
                send_message(sender, f"La valeur choisie n'est pas une puissance valide")
                send_button_message(sender, "Quelle est votre puissance souscrite ?", ["PPP", "PMP", "Recommencer"])
            else:
                sessions[sender]['step'] = 3
                send_button_message(sender, "Est-ce votre première recharge du mois ?", ["Oui", "Non", "Recommencer"])
        elif sessions[sender]['step'] == 3:
            # Mise à jour du timestamp
            sessions[sender]['last_active'] = datetime.now()
            if text.lower() in ['oui', 'non']:
                sessions[sender]['premiere_recharge'] = text.lower() == "oui"
                if sessions[sender]['premiere_recharge'] :
                    sessions[sender]['montant_deja_recharge']=0 
                    sessions[sender]['step'] = 5
                    send_message(sender, "Quel est le montant que vous souhaitez recharger ?")
                    #send_button_message(sender, "", ["Recommencer"])
                else:
                    sessions[sender]['step'] = 4
                    send_message(sender, "Quel est le montant total déjà rechargé ce mois-ci ?") 
                    #send_button_message(sender, "", ["Recommencer"])
            else:  
                send_message(sender, "Merci de répondre par 'oui' ou 'non'.") 
                send_button_message(sender, "", ["Recommencer"])        
        elif sessions[sender]['step'] == 4:
            # Mise à jour du timestamp
            sessions[sender]['last_active'] = datetime.now()
            if not is_valid_amount(text):
                send_message(sender, f"Merci de saisir un montant déja rechargé valide (supérieur à 1.000 FCFA).")
                #send_button_message(sender, "", ["Recommencer"]) 
            else :
                sessions[sender]['montant_deja_recharge'] = float(text)
                sessions[sender]['step'] = 5
                send_message(sender, "Quel est le montant que vous souhaitez recharger ?")
                #send_button_message(sender, "", ["Recommencer"]) 
        elif sessions[sender]['step'] == 5:
            # Mise à jour du timestamp
            sessions[sender]['last_active'] = datetime.now()
            if not is_valid_amount(text):
                send_message(sender, f"Merci de saisir un montant à recharger valide (supérieur à 1.000 FCFA).")
                #send_button_message(sender, "", ["Recommencer"]) 
            else :
                sessions[sender]['step'] = 6
                sessions[sender]['montant_recharge'] = float(text)
                # Calcul
                sessions[sender]['result'] = calcul_kwh(
                    puissance=sessions[sender]['puissance'],
                    montant=float(sessions[sender]['montant_recharge']),
                    cumul_montant=float(sessions[sender]['montant_deja_recharge']),
                    is_premiere_recharge=sessions[sender]['premiere_recharge']
                )
                send_message(sender, f"✅ Vous recevrez environ {sessions[sender]["result"]["kwh"]} kWh.")
                send_button_message(sender, "Voulez-vous voir le détail de cette recharge ?", ["Oui", "Non", "Recommencer"])
        elif sessions[sender]['step'] == 6:
            # Mise à jour du timestamp
            sessions[sender]['last_active'] = datetime.now()
            if text.lower() in ['oui', 'non']:
                if text.lower()=='oui' :
                    '''send_message(sender, f"Voici le détail de votre recharge : \n\n- *Frais de location* : *{sessions[sender]["result"]["location"]}* \n\n- *{sessions[sender]["result"]["quota_tranche_1"]}* kwh en *tranche 1* pour un coût de *{int(sessions[sender]["result"]["cout_tranche_1"]):,} FCFA* \n\n- *{sessions[sender]["result"]["quota_tranche_2"]}* kwh en *tranche 2* pour un coût de *{int(sessions[sender]["result"]["cout_tranche_2"]):,} FCFA* \n\n- *{sessions[sender]["result"]["quota_tranche_3"]}* kwh en *tranche 3* pour un coût de *{int(sessions[sender]["result"]["cout_tranche_3"]):,} FCFA*".replace(",", " "))'''
                    send_message(sender, generer_detail_recharge(sessions[sender]['montant_recharge'],
                                                                 sessions[sender]['result']['detail_tranches'],
                                                                 sessions[sender]['premiere_recharge']))
                send_message(sender, "Merci d'avoir utilisé nos services. A bientôt")              
                del sessions[sender]  # Reset session
            else:  
                send_message(sender, "Merci de répondre par 'oui' ou 'non'.")
                #send_button_message(sender, "", ["Recommencer"]) 


    except Exception as e:
        return f"Erreur : {e}"
    return "OK", 200
      
def send_message(to, text):
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text}
    }
    response = requests.post(URL, headers=headers, json=payload)

def send_button_message(to, question, options):
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {
                "text": question
            },
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {
                            "id": f"option_{i}",
                            "title": opt
                        }
                    } for i, opt in enumerate(options)
                ]
            }
        }
    }
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    requests.post(URL, headers=headers, json=payload)

def send_list_message(to, header_text, body_text, footer_text, button_text, section_title, options):
    """
    Envoie un message interactif de type liste à un utilisateur WhatsApp.

    Args:
        recipient_id (str): Numéro WhatsApp du destinataire au format international.
        header_text (str): Texte de l'en-tête.
        body_text (str): Corps du message.
        footer_text (str): Pied de page du message.
        button_text (str): Texte du bouton pour afficher les options.
        section_title (str): Titre de la section d'options.
        options (list): Liste de tuples (id, title) représentant chaque option.
    """
    
    headers = {
        "Authorization": "Bearer YOUR_ACCESS_TOKEN",
        "Content-Type": "application/json"
    }

    rows = [{"id": opt[0], "title": opt[1]} for opt in options]

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "header": {
               "type": "text",
               "text": header_text
            },
            "body": {
                "text": body_text
            },
            "footer": {
                "text": footer_text
            },
            "action": {
                "button": button_text,
                "sections": [
                    {
                        "title": section_title,
                        "rows": rows
                    }
                ]
            }
        }
    }
    response = requests.post(URL, headers=headers, json=payload)


def is_valid_amount(value):
    try:
        amount = float(value)
        return amount >= 1000
    except:
        return False
def manageTIMEOUTSession(sender):
    session = sessions.get(sender)
    if session:
        last_active = session.get('last_active')
        if last_active and datetime.now() - last_active > timedelta(minutes=TIMEOUT_MINUTES):
            del sessions[sender]
            send_message(sender, "Votre session a expiré après 5 minutes d'inactivité. Veuillez recommencer.")
            return "Session expirée", 200

if __name__ == '__main__':
    '''port = int(os.environ.get("PORT", 5000))
    application.run(host="0.0.0.0", port=port)'''
    application.run(debug=True)
