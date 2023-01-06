from cgi import print_arguments
from http import client, server
import re
import discord
import dotenv
import os
import json, urllib.request
import datetime
import time



from discord.ext import commands
from discord.ext import tasks
from discord.utils import get 
from discord import Message as message
import exceptions
from riotwatcher import LolWatcher, ApiError

dotenv.load_dotenv()
token = os.getenv("TOKEN")

watcher = LolWatcher(os.getenv("RIOT_API_KEY"))

url = "https://ddragon.leagueoflegends.com/cdn/12.6.1/data/en_US/champion.json" #16-7 Latest

champion_data = {}

with urllib.request.urlopen(url) as url:
    champion_data = json.loads(url.read().decode())

data = champion_data['data']

latest_games_ammount = 1


bot = commands.Bot(command_prefix="$",description="Non Oficial League Utility Bot")

global track_list 
track_list = []


@bot.command()
async def ping(ctx):
    await ctx.send("pong")

@bot.command()
async def commands(ctx):
    await ctx.author.send("$ping - Answers with pong.\n$help - Shows this message.\n$latestgames - Shows the result of the latest RANKED game. You can configure to print up to five matches at a time. \n$changelimit - Changes the amount of matches printed with the command above. Max ammunt is five.")

@bot.command()
async def searchsummoner(ctx, region, *args):
    try:
        if (valid_region(region)):
            converted_region = regionConverter(region)
            summoner = watcher.summoner.by_name(converted_region,"".join(args))
            tier_info = watcher.league.by_summoner(converted_region, summoner['id'])
            masteries = watcher.champion_mastery.by_summoner(converted_region, summoner['id'])

            for obj in data:
                if data[obj]['key'] == str(masteries[0]['championId']):
                    champion_name = data[obj]['name']
                    break
            curr = os.getcwd()
            os.chdir("src/img")
            formatted_winrate = "{:.2f}".format(returnWinrate(tier_info[0]['wins'],tier_info[0]['losses']))
            file = discord.File(returnImageName(tier_info[0]['tier']), filename=returnImageName(tier_info[0]['tier']))
            name = summoner['name']
            embed=discord.Embed(title="Summoner Lookup", url="https://"+region+".op.gg/summoners/"+region+"/"+ name.replace(" ",""), description= "Click the blue text above for the OP.GG profile", color=0xFF5733)
            embed.set_author(name="LeaguePy Bot", url="https://twitter.com/kakyosimp", icon_url="https://cdn.discordapp.com/avatars/995730184143646821/ba716523b0d442ada25cec8e52b63736.webp?size=80")
            embed.set_thumbnail(url=f"attachment://{returnImageName(tier_info[0]['tier'])}")
            embed.add_field(name="Summoner's info", value=f"Rank: {tier_info[0]['tier']} {tier_info[0]['rank']} {tier_info[0]['leaguePoints']} LP \n Wins: {tier_info[0]['wins']}  Losses: {tier_info[0]['losses']}\n Winrate: {formatted_winrate} \nOn winstreak? {onWinStreak(tier_info)} "  , inline=False)
            embed.add_field(name="Other info", value=f"Champ with most mastery: {champion_name} at Level {masteries[0]['championLevel']} \n Mastery Points: {masteries[0]['championPoints']}", inline=False)
            await ctx.send(file=file,embed=embed)
            os.chdir(curr)
        else:
            await ctx.send("Invalid Region")
    except ApiError as e:
        if e.response.status_code == 404:
            await ctx.send("Summoner not found or hasn't played ranked games yet/for a long time.")
        elif e.response.status_code == 429:
            await ctx.send("Too much requests. Try again in "+ str(e.response.headers['Retry-After']) + " seconds")
    except exceptions.invalidRegionException as e:
        await ctx.send(e)
    

def returnWinrate(wins,losses):
    return (wins/(wins+losses))*100

def onWinStreak(tier_info):
    return "Yes" if tier_info[0]['hotStreak'] is True else "No"

def returnImageName(rank):
    return "emblem_" + rank.lower() + ".png"

def valid_region(region):
    if (regionConverter(region) == "Invalid Region"):
        raise exceptions.invalidRegionException("Invalid Region. Please use one of the following: ""BR"",""EUW"",""KR"",""LAN"",""LAS"",""NA"",""OCE"",""RU"",""TR""")
    else:
        return True
        


def regionConverter(region):
    if (region == "BR"):
        return "BR1"
    elif (region == "EUNE"):
        return "EUN1"
    elif (region == "EUW"):
        return "EUW1"
    elif (region == "JP"):
        return "JP1"
    elif (region == "KR"):
        return "KR"
    elif (region == "LAN"):
        return "LA1"
    elif (region == "LAS"):
        return "LA2"
    elif (region == "NA"):
        return "NA1"
    elif (region == "OCE"):
        return "OC1"
    elif (region == "TR"):
        return "TR1"
    elif (region == "RU"):
        return "RU"
    elif (region == "PBE"):
        return "PBE"
    else:
        return "Invalid Region"

@bot.command()    
async def latestgames(ctx, region, *args):
    try:
        if (valid_region(region)):
            converted_region = regionConverter(region)
            summoner = watcher.summoner.by_name(converted_region,"".join(args))
            summoner_puuid = summoner['puuid']
            match_info = watcher.match.matchlist_by_puuid(converted_region, summoner_puuid,0,latest_games_ammount,None,"ranked",None,None)
            print(match_info)
            await summoner_match_performance_embedder(ctx,converted_region,match_info,summoner_puuid)

        else:
            await ctx.send("Invalid Region")
    except ApiError as e:
        if e.response.status_code == 404:
            await ctx.send("Summoner not found")
        elif e.response.status_code == 429:
            await ctx.send("Too much requests. Try again in "+ str(e.response.headers['Retry-After']) + " seconds")
    except exceptions.invalidRegionException as e:
        await ctx.send(e)


@bot.command()
async def changelimit(ctx, limit):
    global latest_games_ammount
    if (limit.isnumeric() == False | int(limit)<=0 | int(limit)>=5): 
            await ctx.send("The limit must be an integer and no more than 5")
    else:
        latest_games_ammount = int(limit)
        await ctx.send("Limit changed to " + str(limit))    

@bot.command()
async def printlimit(ctx):
    await ctx.send("The limit is " + str(latest_games_ammount))


@bot.command()
async def trackplayer(ctx,region, *args):
    try:
        if (valid_region(region)):
            converted_region = regionConverter(region)
            summoner = watcher.summoner.by_name(converted_region,"".join(args))
            if (len(track_list)<=3):
                tracked_summoner = {
                    "name": "".join(args).lower(),
                    "region": converted_region,
                    "puuid": summoner['puuid']
                }
                track_list.append(tracked_summoner)
                await ctx.send("Summoner "+ tracked_summoner["name"] + " from " + tracked_summoner["region"] +" added to tracking list. Data might be lost if the bot is restarted.")
            else:
                await ctx.send("The tracking list is full. Remove an summoner to add another one. (Limit is 5)")
        else:
            await ctx.send("Invalid Region")
    except ApiError as e:
        if e.response.status_code == 404:
            await ctx.send("Summoner not found")
        elif e.response.status_code == 429:
            await ctx.send("Too much requests. Try again in "+ str(e.response.headers['Retry-After']) + " seconds")
    except exceptions.invalidRegionException as e:
        await ctx.send(e)

@bot.command()
async def untrackplayer(ctx, region,*args):
    try:
        if (valid_region(region)):
            converted_region = regionConverter(region)
            tracked_summoner = {
                "name": "".join(args).lower(),
                "region": converted_region,
            }
            for summoner in track_list:
                if (summoner["name"] == tracked_summoner["name"] and summoner["region"] == tracked_summoner["region"]):
                    track_list.remove(summoner)
                    await ctx.send("Untracked " + tracked_summoner["name"] + " in " + tracked_summoner["region"])
                    return
            
            await ctx.send("Summoner not found in track list")
        else:
            await ctx.send("Invalid Region")
    except ApiError as e:
        if e.response.status_code == 404:
            await ctx.send("Summoner not found")
        elif e.response.status_code == 429:
            await ctx.send("Too much requests. Try again in "+ str(e.response.headers['Retry-After']) + " seconds")
    except exceptions.invalidRegionException as e:
        await ctx.send(e)

@bot.command()
async def tracklist(ctx):
    aux_string = ""
    if (len(track_list) == 0):
        await ctx.send("The tracking list is empty")
    else:
        await ctx.send("Tracked players: ")
        for tracked_summoner in track_list:
            aux_string += tracked_summoner["name"] + " from " + tracked_summoner["region"] + "\n"
        await ctx.send(aux_string)


@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name="Use $commands for commands"))
    loopGameTracker.start()
    print("Started up sucessfuly")





@tasks.loop(minutes=5)
async def loopGameTracker():
    chan = bot.get_channel(1012332277168083024)
    name = "game_tracker"
    if not get(server.channels, name=name):
        await bot.create_channel(server, name)
    if (len(track_list) != 0):
        for tracked_summoner in track_list:
            try:
                fivemins = datetime.datetime.now() - datetime.timedelta(minutes=5)
                fivemins_epoch = int(time.mktime(fivemins.timetuple()))
                now = datetime.datetime.now()
                now_epoch = int(time.mktime(now.timetuple()))
                summoner = watcher.summoner.by_name(tracked_summoner["region"],tracked_summoner["name"])
                match_info = watcher.match.matchlist_by_puuid(tracked_summoner["region"], summoner['puuid'],0,latest_games_ammount,None,"ranked",fivemins_epoch,now_epoch)
                if not match_info:
                    await chan.send(summoner['name'] + " from " + tracked_summoner["region"] + " has not finished playing a game in the last 5 minutes")
                else:
                    await chan.send(summoner['name'] + " from " + tracked_summoner["region"] + " has finished playing a game in the last 5 minutes")
                    await summoner_match_performance_embedder(chan,tracked_summoner["region"],match_info,summoner['puuid'])
            except ApiError as e:
                if e.response.status_code == 429:
                    await chan.send("Too much requests. Try again in "+ str(e.response.headers['Retry-After']) + " seconds")
            except exceptions.invalidRegionException as e:
                await chan.send(e)
    
            
    



def puuid_to_summoner(region,puuid):
    name = watcher.summoner.by_puuid(region,puuid)['name']
    return name


async def summoner_match_performance_embedder(chan,region,match_info,summoner_puuid):
    curr = os.getcwd()
    for match in match_info:
            aux_match = watcher.match.by_id(region, match)
            inf = aux_match["info"]
            for participant in inf["participants"]:
                if (participant["summonerName"] == puuid_to_summoner(region,summoner_puuid)):
                    if (participant["win"] == True):
                        os.chdir("src/img")
                        image_result = discord.File("victory.png","victory.png")
                        result = "Victory"
                    else:
                        os.chdir("src/img")
                        image_result = discord.File("defeat.png","victory.png")
                        result = "Defeat"    
                    embed=discord.Embed(title="Match Information for game "+ str(match), description= "Requested summoner: "+ participant["summonerName"] +"\nGame result: " + result + "\nKDA: "+ str(participant["kills"]) + "/" + str(participant["deaths"]) + "/" + str(participant["assists"])+ "\n Champion played: " + participant["championName"], color=0xFF5733)
                    embed.set_author(name="LeaguePy Bot", url="https://twitter.com/kakyosimp", icon_url="https://cdn.discordapp.com/avatars/995730184143646821/ba716523b0d442ada25cec8e52b63736.webp?size=80")
                    embed.set_thumbnail(url=f"attachment://{image_result.filename}")
                    embed.add_field(name="Damage Details", value="Damage Dealt: " + str(participant["totalDamageDealtToChampions"]) + "\n Damage Taken: " + str(participant["totalDamageTaken"]), inline= False)
                    embed.add_field(name="Healing", value="Healing Done: " + str(participant["totalHeal"]) + "\n Healing done on teammates: "+str(participant["totalHealsOnTeammates"]), inline=True)
                    embed.add_field(name="Other data", value="Largest Multikill: " + str(participant["largestMultiKill"]), inline=True)
                    await chan.send(embed=embed, file=image_result)
                    os.chdir(curr)
                    
bot.run(token)
    