from flask import Flask, request
import re
# import instaloader
# import pandas as pd
import urllib.request
import os
import json
# from instaloader.exceptions import ProfileNotExistsException
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from langchain.llms.openai import OpenAI
from langchain.llms import OpenAI
from langchain import OpenAI
# from colorama import init, Fore, Back, Style
from colorama import Fore

app = Flask(__name__)

# url = "https://puntodestino.com.mx/"

# bot = instaloader.Instaloader()

social = ["facebook.com", "instagram.com", "linkedin.com"]


@app.route("/bbdd", methods=['GET'])
def syncBBDD():
    args = request.args
    return args.get("unParam")


@app.route("/sync", methods=['GET'])
def syncUser():
    args = request.args
    url = args.get("website")

    if (url and url.endswith("/") == False):
        url = url + "/"

    instagram_followers, instagram_link, facebook_followers, facebook_link = social_findings(
        url)

    url_text = extract_text(url)

    llm = openai_login()

    prompt = f"""You are a helpful marketing assistant, who can explain concepts in an easy-to-understand manner. 
          Answer the following question succintly in spanish. Give short answer
          The site information is delimited with triple backticks.
          You can only give short answers with "Yes" or "No".
          Context: Una agencia de marketing o publicidad es una empresa encargada de gestionar las actividades de 
          Marketing de sus clientes, con el objetivo de atraer consumidores, incrementar las ventas, fortalecer el 
          branding y generar valor para el mercado
          Question: Según el texto: '''{url_text} '''
          ¿{url} es una agencia de marketing o publicidad?
          Answer: """
    is_agency = llm(prompt)

    prompt = f"""You are a helpful marketing assistant, who can explain concepts in an easy-to-understand manner. 
          Answer the following question succintly in spanish. You can only answer with the industry 
          Context: La empresa solo comprende las siguientes industrias:
            MARKETING ADVERTISING
            HEALTH BEAUTY
            EDUCATION
            FINANCE
            NON PROFIT
            TRAVEL TOURISM
            INDUSTRIAL
            NOT SET
            AUTOMOTIVE
            SERVICES
            FOOD DRINKS
            CONSULTING
            REAL ESTATE
            TV RADIO
            SOFTWARE
            DESIGN PHOTOGRAPHY
            HOME DECOR
            INFORMATION TECHNOLOGY
            INSURANCE
            EVENTS ENTERTAINMENT
            TEXTILE
            OTHER
            SECURITY
            RETAIL
            SPORTS
            LEGAL ACCOUNTING

          Question: Según el texto {url_text} ¿Qué tipo de industria es a la que se dedica {url}? Responde solamente con el nombre de la industria. Ejemplo, si es de educación solo responde EDUCATION.
          Answer: """

    vertical = llm(prompt)

    prompt = f"""You are a helpful marketing assistant, who can explain concepts in an easy-to-understand manner. 
          Answer the following question succintly in spanish. Give short answer. 
          You can only give short answers with no more than 15 words
          Question: Según el texto {url_text} ¿A qué se dedica el sitio {url}?
          Answer: """

    description = llm(prompt)

    print(Fore.RED + f"""Se ha obtenido la siguiente información de usuario:
    Contexto de la empresa: {description}
    ¿Es una agencia?: {is_agency}
    Industria: {vertical}
    Facebook: {facebook_followers} Seguidores. Enlace a Facebook: {facebook_link}
    Instagram: {instagram_followers} Seguidores. Enlace a Instagram: {instagram_link}
    """)

    data = {
        "context": description,
        "is_agency": is_agency,
        "industry": vertical,
        "facebook": {
            "followers": facebook_followers,
            "link": facebook_link
        },
        "instagram": {
            "followers": instagram_followers,
            "link": instagram_link
        }
    }

    json_object = json.dumps(data, indent=4)
    return json_object


def openai_login():
    openai_token = read_json("gpt.json")
    openai_api_key = os.environ.get('OPENAI_API_KEY', openai_token)
    llm = OpenAI(model_name='text-davinci-003', openai_api_key=openai_api_key)
    return llm


def read_json(file_name):
    try:
        json_file = open(file_name, "r")
        content = json.load(json_file)
        json_file.close()
        return content['token']
    except FileNotFoundError:
        print(f"El archivo '{file_name}' no existe.")
    except json.JSONDecodeError:
        print(f"El archivo '{file_name}' no es válido JSON.")


def find_social_links(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        response = urllib.request.urlopen(req)
        html_code = response.read().decode()
        soup = BeautifulSoup(html_code, 'html.parser')
        links = soup.find_all('a', href=True)
        external_urls = []
        for link in links:
            href = link['href']
            parsed_url = urlparse(href)
            if parsed_url.netloc != '' and href:
                if any(palabra.lower() in href.lower() for palabra in social):
                    external_urls.append(href)
    except urllib.error.HTTPError as e:
        print(f"Error {e.code}: {e.reason}")
    return external_urls


def extract_instagram_username(url):
    parsed_url = urlparse(url)
    netloc = parsed_url.netloc.lstrip('www.')
    if netloc == 'instagram.com':
        path_parts = parsed_url.path.rstrip('/').split('/')
        if len(path_parts) > 1:
            return path_parts[1]
    return None


def instagram_information(instagram_user):
    try:
        url = f"https://www.instagram.com/{instagram_user}/?hl=es"
        req = urllib.request.Request(
            url, headers={'User-Agent': 'Mozilla/5.0'})
        response = urllib.request.urlopen(req)
        html_code = response.read().decode()
        soup = BeautifulSoup(html_code, 'html.parser')
        meta_tag = soup.find('meta', {'name': 'description'})
        if meta_tag:
            description = meta_tag['content']
        match = re.search(r'([\d,.]+)\s?([KkMm]?) seguidores', description)
        if match:
            followers_str = match.group(1)
            followers_str = followers_str.replace(',', '').replace('.', '')
        if '.' in followers_str:
            followers = float(followers_str)
        else:
            followers = int(followers_str)
        unidad = match.group(2).lower()
        if unidad == 'k':
            followers *= 1000
        followers = int(round(followers))
        return followers
    except urllib.error.HTTPError as e:
        print(f"Error {e.code}: {e.reason}")


def extract_text(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        response = urllib.request.urlopen(req)
        html_code = response.read().decode()
        soup = BeautifulSoup(html_code, 'html.parser')
        relevant_text = '\n'.join(
            line.strip() for line in soup.get_text().splitlines() if line.strip())
    except urllib.error.HTTPError as e:
        print(f"Error {e.code}: {e.reason}")


def get_facebook_followers(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        likes = 0
        response = urllib.request.urlopen(req)
        html_code = response.read().decode()
        soup = BeautifulSoup(html_code, 'html.parser')
        meta_tag = soup.find('meta', {'name': 'description'})
        if meta_tag:
            description = meta_tag['content']
        patron = r'\d{1,3}(?:\.\d{3})+'
        result = re.search(patron, description)
        if result:
            likes = result.group()
            likes = int(likes.replace('.', ''))
        return result
    except urllib.error.HTTPError as e:
        print(f"Error {e.code}: {e.reason}")


def social_findings(url):
    social_links = find_social_links(url)
    instagram_followers = 0
    instagram_link = "No tiene cuenta"
    facebook_followers = 0
    facebook_link = "No tiene cuenta"
    for link in social_links:
        if "instagram" in link:
            username = extract_instagram_username(link)
            instagram_followers = instagram_information(username)
            instagram_link = link
        if "facebook" in link:
            facebook_followers = get_facebook_followers(link)
            facebook_link = link
    return instagram_followers, instagram_link, facebook_followers, facebook_link


if __name__ == "__main__":
    app.run()
