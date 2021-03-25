from  discord.ext import commands
import discord
import wolframalpha
import numpy as np
from PIL import Image
from PIL import ImageOps
import matplotlib.pyplot as plt
from io import BytesIO
import base64
import requests
import pandas as pd
from itertools import permutations
import sys
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import webcolors

# TODO(#1): this is disgusting figure out cogs

bot = commands.Bot(command_prefix ='!')
with open("bot.txt") as f:
    bot_cred = f.read().strip()

@bot.event
async def on_ready():
    print('logged in')
    print(bot.user.name)
    print(bot.user.id)

@bot.command()
async def  wolfy(ctx, query: str,):
    'takes a problem and returns a solution for example <wolfy \'laplace transform of 1\' will return \'1/s\''
    with open("wolf.txt") as f:
        wolf_cred = f.read().strip()
        
    client = wolframalpha.Client(wolf_cred)
    
    res = client.query(query)
    output = next(res.results).text
    await ctx.send(output)

@bot.command()
async def ping(ctx):
    '\tPONG'
    await ctx.send('PONG')

@bot.command()
async def dweeb(ctx):
    '\ttells you were the bot is'
    await ctx.send('D.W.E.E.B: Da Worst Electrical Engineering Bot\n https://github.com/DrAtomic/dweeb')

@bot.command()
async def ohms(ctx):
    '\ttells you ohms law'
    await ctx.send('V=IR')

@bot.command(pass_context=True)
async def timeDomain(ctx):
    '\ttakes a picture and returns a squiggley picture'
    attachment_url = ctx.message.attachments[0].url
    response = requests.get(attachment_url)
    
    #grayscales the image and makes a sin wave based on the intensity(not sure if right word)?
    basewidth = 130         #Numbers of pixels for the base (the original aspect ratio is preserved)
    img = Image.open(BytesIO(response.content)).convert('LA')
    wpercent = (basewidth/float(img.size[0]))
    hsize = int((float(img.size[1])*float(wpercent))/3)
    img = img.resize((basewidth,hsize), Image.ANTIALIAS)
    img = ImageOps.flip(img)
    img.load()
    data = np.asarray( img, dtype="int32")

    #Replace by any bijection from [0,1] to [0,1] to adjust the overall repartition of the details
    def f(x):
        return x**2
    
    
    arr=[]
    for lignes in data:
        l=[0]
        for e in lignes:
            l.append(l[-1]+f(1-e[0]/256))
        arr.append(l)
        
    #This matches the sines with the correct frequenty, and make sure it's continuous
    def freq(t,l):
        ind = int(t)
        m = (l[ind+1]-l[ind])
        p = l[ind] - m*ind
        return m*t + p
    
    def s(t,l):
        return 0.8*np.sin(2*np.pi*freq(t,l))
    
    #Change this n to adapt the size of the display
    n = 4
    fig = plt.figure(figsize = (n,n*3*hsize/basewidth))
    fig.patch.set_visible(False)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis('off')
    
 
    for i in range(len(arr)):
        l = arr[i]
        x = np.linspace(0,basewidth,10000)[:-1]
        y = [3*i +1+s(e,l) for e in x]
        plt.plot(x,y,c='white',linewidth=0.7)
    plt.savefig("temp.png",dpi=1000)
    
    
    await ctx.send(file=discord.File('temp.png'))
    
@bot.command(pass_context=True)
async def banCheck(ctx):
    '\tchecks for banned cards in bad format'
    with open('banlist.txt','r') as file:
        ban_list = file.read().splitlines()


    attachment_url = ctx.message.attachments[0].url
    response = requests.get(attachment_url)
    input_file = response.content
    input_file = input_file.decode("utf-8")
    deck = input_file.splitlines()
    
    banned_cards = []
    
    for card in deck:
        for banned_card in ban_list:
            if banned_card in card:
                banned_cards.append(card)
    await ctx.send(banned_cards)
    
@bot.command(pass_context=True)
async def fabric(ctx,type_of_fabric,cost_of_fabric,length_of_fabric,password):
    '\tadds fabric to inventory sheet'
    with open("fabric.txt") as f:
        fabric = f.read().strip()

    if password == fabric:
        
        scope = ["https://spreadsheets.google.com/feeds",'https://www.googleapis.com/auth/spreadsheets',"https://www.googleapis.com/auth/drive.file","https://www.googleapis.com/auth/drive"]
        
        creds = ServiceAccountCredentials.from_json_keyfile_name("credfab.json",scope)
        
        client = gspread.authorize(creds)
        
        sheet = client.open("inventory").sheet1
        
        data = sheet.get_all_records()
        
        
        attachment_url = ctx.message.attachments[0].url
        response = requests.get(attachment_url)
        path_to_image = response.content
        cost_per_yard = float(cost_of_fabric) / float(length_of_fabric)
        
        # color classifier
        def closest_color(requested_color):
            min_colors = {}
            for key, name in webcolors.CSS3_HEX_TO_NAMES.items():
                r_c, g_c, b_c = webcolors.hex_to_rgb(key)
                rd = (r_c - requested_color[0]) ** 2
                gd = (g_c - requested_color[1]) ** 2
                bd = (b_c - requested_color[2]) ** 2
                min_colors[(rd + gd + bd)] = name
            return min_colors[min(min_colors.keys())]
        
        # get image and avg
        
        
        im = Image.open(BytesIO(response.content))
        image = np.asarray(im)
        width, height,d = image.shape
        center_x = width/2
        center_y = height/2
        
        left =round(center_x-150)
        top =round(center_y+150)
        right =round(center_x+150)
        bottom =round(center_y-150)
        croped = image[left:right,bottom:top]
        im1 = Image.fromarray(croped)
        
        buffer = BytesIO()
        im1.save(buffer, format="JPEG")
        myimage = buffer.getvalue()
        bytes_data = base64.b64encode(myimage)
        
        average = (croped.sum(axis=1).sum(axis=0)) / (croped.shape[0]*croped.shape[1])
        
        color_name = closest_color(average)
        # end of color classifier

        #append
        
        row = [color_name, type_of_fabric, str(cost_per_yard), length_of_fabric, str(bytes_data)]
        sheet.append_row(row)
        await ctx.send('done')
    else:
        await ctx.send('Access denied')
    
    
@bot.command()
async def mtg(ctx,colors):
    "takes a color combination returns a .cod file of commander lands \n also if you play hmuuuuuu"
    
    def search(values,searchFor):
        for k in values.get('Colors'):
            if searchFor in k:
                return values

    def color_or(dictionary,color):
        temp =[]
        for color in colors:
            for i in dictionary:
                temp.append(search(i,color))
        result = [x for x in temp if x is not None]
        return result


    def fetch(list_dictionaries):
        if any(t == "fetch" for t in list_dictionaries.values()):
            return list_dictionaries

    def color_and(dictionary, color):
        temp = []
        perm = []
        for i in range(len(color)+1):
            perm.append(["".join(map(str,comb)) for comb in permutations(color,i)])
        flatten = lambda t: [item for sublist in t for item in sublist]
        perm = flatten(perm)
        for c in perm:
            for i in dictionary:
                if c == i.get('Colors'):
                    temp.append(i)
        result = [x for x in temp if x is not None]
        return(result)


    scope = ["https://spreadsheets.google.com/feeds",'https://www.googleapis.com/auth/spreadsheets',"https://www.googleapis.com/auth/drive.file","https://www.googleapis.com/auth/drive"]

    creds = ServiceAccountCredentials.from_json_keyfile_name("creds.json",scope)

    client = gspread.authorize(creds)

    sheet = client.open("cards").sheet1

    data = sheet.get_all_records()

    df = pd.DataFrame(data)

    test = df.to_dict(orient='records')
    x = color_or(test, colors)
    full_dict =[]

    for i in test:
        if any(t == "all" for t in i.values()):
            full_dict.append(i)
            
    for i in x:
        full_dict.append(fetch(i))
        if any(t == "basic" for t in i.values()):
            full_dict.append(i)
    
    full_dict = [t for t in full_dict if t is not None]
    full_dict = [dict(t) for t in {tuple(d.items()) for d in full_dict}]

    y = color_and(test,colors)
    dict_of_cards = []
    for i in y:
       dict_of_cards.append(i.get('Title'))
    for i in full_dict:
       dict_of_cards.append(i.get('Title'))

    list_of_cards = list(dict.fromkeys(dict_of_cards))
    f = open(str(colors)+".txt",'w')
    for name in list_of_cards:
        f.write(str(name)+"\n")
    f.close()
    
    with open(str(colors)+".txt","rb") as f:
        await ctx.send("here ya go",file=discord.File(f,str(colors)+".txt"))
    f.close()
    os.remove(str(colors)+".txt")


bot.run(bot_cred)

