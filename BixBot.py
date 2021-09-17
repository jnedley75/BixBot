import sys
sys.path.insert(1, r'C:\Users\jjn0004.HS\OneDrive\Discord\BixBot\packages')
import discord
import os
import nacl
from discord.ext import commands,tasks
from discord.utils import get
import urllib.parse, urllib.request, re
import youtube_dl
import lxml
from lxml import etree
from xml.etree import ElementTree
from dotenv import load_dotenv
from pathlib import Path
#------------------------------------------------------------------
#                   ____     _             ____           __
#                 / __ )   (_)   _  __   / __ )  ____   / /_
#               / __  |  / /   | |/_/  / __  | / __ \ / __/
#             / /_/ /  / /   _>  <   / /_/ / / /_/ // /_
#           /_____/  /_/   /_/|_|  /_____/  \____/ \__/
#
#------------------------------------------------------------------
load_dotenv(Path('discord.env'))
BOT_TOKEN = os.getenv('TOKEN')

intents = discord.Intents().all()
bot = commands.Bot(command_prefix="--",intents=intents)


@bot.event
async def on_ready():
    print('{0.user}'.format(bot).split('#')[0] + ' is running...')

#Music Stuff
youtube_dl.utils.bug_reports_message = lambda: ''

ytdl_format_options = {
    'format': 'bestaudio/best',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0' # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = ""

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]
        filename = data['title'] if stream else ytdl.prepare_filename(data)
        return filename

Queue = []

#End of Music Stuff


@bot.command(name='join', help='Tells the bot to join the voice channel')
async def join(ctx):
    if not ctx.message.author.voice:
        await ctx.send("{} is not connected to a voice channel".format(ctx.message.author.name))
        return
    else:
        channel = ctx.message.author.voice.channel
    await channel.connect()

@bot.command(name='leave', help='To make the bot leave the voice channel')
async def leave(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_connected():
        await voice_client.disconnect()
    else:
        await ctx.send("The bot is not connected to a voice channel.")


#Start of music controls
@bot.command(name='play', help='To play song')
async def play(ctx, *args):
    count = 0;
    media = " ".join(args)
    try :
        server = ctx.message.guild
        voice_channel = server.voice_client

        if media.startswith("https://"):
            media_url = media.split("/")[2]
            if media_url.startswith("open.spotify.com"):
                print("we did this correct")
            elif media_url.startswith("www.youtube.com"):
                async with ctx.typing():
                    try:
                        filename = await YTDLSource.from_url(media, loop=bot.loop)
                        try:
                            voice_channel.play(discord.FFmpegPCMAudio(executable="ffmpeg.exe", source=filename))
                        except discord.errors.ClientException as e:
                            print(e)
                            await stop(ctx)
                            await play(ctx, media)
                    except:
                        print("here")
                        await stop(ctx)
                        await play(ctx, media)
                await ctx.send('**Now playing:** {}'.format(filename))
        else:
            query_string = urllib.parse.urlencode({'search_query': media})
            htm_content = urllib.request.urlopen('http://www.youtube.com/results?' + query_string)
            search_results = re.findall(r'/watch\?v=(.{11})', htm_content.read().decode())

            async with ctx.typing():
                filename = await YTDLSource.from_url('http://www.youtube.com/watch?v=' + search_results[0], loop=bot.loop)
                try:
                    voice_channel.play(discord.FFmpegPCMAudio(executable="ffmpeg.exe", source=filename))
                except discord.errors.ClientException as e:
                    print(e)
                    await stop(ctx)
                    await play(ctx, media)
            await ctx.send('**Now playing:** {}'.format(filename))
    except:
        await join(ctx)
        await play(ctx, media)

@bot.command(name='playNext', help='This command adds a song to the queue to be played')
async def playNext(ctx, *args):
    media = " ".join(args)

    addToQueue(media)
    youtube = etree.HTML(urllib.request.urlopen(media).read())
    video_title = "".join(youtube.xpath('//meta[@name="title"]/@content'))
    await ctx.send("Added **" + video_title + "** to the queue")

@bot.command(name='removeSong', help='This command allows you to remove a song from the queue')
async def removeSong(ctx):
    queue = showQueue()
    if not queue:
        async with ctx.typing():
            await ctx.channel.send("You've got nothing in the queue buddy. What're you doing");
    else:
        queue.set_footer(text="Type index number (1 - 10) to remove a song `(Type 'cancel' to quit)`");
        async with ctx.typing():
            await ctx.channel.send(embed=queue);
        validChoice = False
        while validChoice == False:
            choice = await bot.wait_for('message', check=lambda message: message.author == ctx.author)
            try:
                if (1 <= int(choice.content) <= 10):
                    validChoice = True
                else:
                    await ctx.channel.send('I said 1-10, come on now...')
            except:
                if choice.content == "cancel":
                    validChoice = True
                else:
                    await ctx.channel.send('You do know 1-10, are numbers right?')

        if(choice.content == "cancel"):
            await ctx.channel.send('Herrrrrrrd!')
        else:
            removeFromQueue(int(choice.content))
            async with ctx.typing():
                songToRemove = songs.split("\n")[int(choice.content)-1]
                songToRemove = songToRemove[songToRemove.index("`", 1, 4)+1:]
                await ctx.channel.send("**" + songToRemove + "** has been removed from the queue")


def addToQueue(url):
    if url.startswith("https://"):
        fixed_url = url.split("/")[2]
        if fixed_url.startswith("open.spotify.com"):
            print("we did this correct")
        elif fixed_url.startswith("www.youtube.com"):
                Queue.append(url);

def removeFromQueue(index):
    Queue.pop(index-1)

@bot.command(name='showQueue', help='This command will display the queue')
async def showQueue(ctx):
    queue = showQueueLogic()
    if not queue:
        async with ctx.typing():
            await ctx.channel.send("You've got nothing in the queue buddy. What're you doing");
    else:
        async with ctx.typing():
            await ctx.channel.send("You've got nothing in the queue buddy. What're you doing");

def showQueueLogic():
    if not Queue:
        return False;
    count = 0
    songs = ""
    for x in Queue:
        if count == (len(Queue)):
            break
        youtube = etree.HTML(urllib.request.urlopen(x).read())
        video_title = "".join(youtube.xpath('//meta[@name="title"]/@content'))
        songs = songs + "`" + str(count+1) + "` " + video_title + "\n"
        count += 1

    QueueList_embed=discord.Embed(title="Queue", description=songs, color=0x61b8f5);

    return QueueList_embed




@bot.command(name='search', help='This command searches for a song')
async def search(ctx, *args):
    query = " ".join(args);

    if not query:
        async with ctx.typing():
            await ctx.channel.send('What would you like to search for?')
            fixedQuery = await bot.wait_for('message', check=lambda message: message.author == ctx.author)
            await search(ctx, fixedQuery)
    else:
        query_string = urllib.parse.urlencode({'search_query': query})
        htm_content = urllib.request.urlopen('http://www.youtube.com/results?' + query_string)
        search_results = re.findall(r'/watch\?v=(.{11})', htm_content.read().decode())

        async with ctx.typing():
            count = 0
            results = ""
            for x in search_results:
                if(count == 10):
                    break
                youtube = etree.HTML(urllib.request.urlopen('http://www.youtube.com/watch?v=' + search_results[count]).read())
                video_title = "".join(youtube.xpath('//meta[@name="title"]/@content'))
                results = results + "`" + str(count+1) + "` " + video_title + "\n"
                count += 1

            Result_embed=discord.Embed(title="Search Results", description=results[0: int(len(results) - 2)], color=0x61b8f5);
            Result_embed.set_footer(text="Type index number (1 - 10) to pick a song `(Type 'cancel' to quit)`");

            await ctx.channel.send(embed=Result_embed);

            validChoice = False
            while validChoice == False:
                choice = await bot.wait_for('message', check=lambda message: message.author == ctx.author)
                try:
                    if (1 <= int(choice.content) <= 10):
                        validChoice = True
                    else:
                        await ctx.channel.send('I said 1-10, come on now...')
                except:
                    if choice.content == "cancel":
                        validChoice = True
                    else:
                        await ctx.channel.send('You do know 1-10, are numbers right?')


            if(choice.content == "cancel"):
                await ctx.channel.send('Herrrrrrrd!')
            else:
                await play(ctx, "http://www.youtube.com/watch?v=" + search_results[int(choice.content) - 1])


@bot.command(name='pause', help='This command pauses the song')
async def pause(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_playing():
        await voice_client.pause()
    else:
        await ctx.send("The bot is not playing anything at the moment.")

@bot.command(name='resume', help='Resumes the song')
async def resume(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_paused():
        await voice_client.resume()
    else:
        await ctx.send("The bot was not playing anything before this. Use `play [url]` command")

@bot.command(name='stop', help='Stops the song')
async def stop(ctx):
    voice_client = ctx.message.guild.voice_client
    if voice_client.is_playing():
        await voice_client.stop()
    else:
        await ctx.send("The bot is not playing anything at the moment.")

#End of Music Controls
#----------------------------------------------------------------------------------------------------------------------------------------
#End of msuic stuff

@bot.command(name='payBitdefender', help='To make the bot display an embed of options for payment')
async def payBitdefender(message):
    embed=discord.Embed(title="Bitdefender Antivirus Payment",
    description="Please use one of the hyperlinks to make your payment.",
    color=0x61b8f5);

    embed.set_author(name=message.author.display_name,
    icon_url=message.author.avatar_url);

    embed.add_field(name="Venmo", value="[Pay with Venmo](https://www.venmo.com/u/jeffnedley)", inline=False);
    embed.add_field(name="Paypal", value="[Pay with PayPal](https://paypal.me/jeffNedley)", inline=False);

    await message.channel.send(embed=embed);


@bot.event
async def on_message(message):
    await bot.process_commands(message)
    if message.author == bot.user:
        return

    if message.content.startswith('$hello'):
        await message.channel.send('Hello!')

bot.run(str(BOT_TOKEN))
