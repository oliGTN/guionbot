import requests
import os
import math
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import json

import goutils
import data

font = ImageFont.truetype("IMAGES"+os.path.sep+"arial.ttf", 24)

NAME_HEIGHT = 30
PORTRAIT_SIZE = 168
MAX_WIDTH_PORTRAITS = 10

dict_colors = {}
dict_colors["blue"] = (0, 0, 255)
dict_colors["bright_orange"] = (255, 200, 10)
dict_colors["brown"] = (128, 0, 0)
dict_colors["gold"] = (255, 200, 10)
dict_colors["green"] = (0, 255, 0)
dict_colors["purple"] = (100, 30, 150)
dict_colors["white"] = (255, 255, 255)
dict_colors["red"] = (128, 0, 0)
dict_colors["bright_blue"] = (128, 128, 255)
dict_colors["dark_blue"] = (0, 0, 255)

def get_image_from_id(character_id):
    character_img_name = 'IMAGES'+os.path.sep+'CHARACTERS'+os.path.sep+character_id+'.png'
    if not os.path.exists(character_img_name):
        swgohgg_characters_url = 'http://api.swgoh.gg/characters'
        goutils.log2("DBG", "Get data from " + swgohgg_characters_url)
        r = requests.get(swgohgg_characters_url, allow_redirects=True)
        #print(r.content[:200])
        list_characters = json.loads(r.content.decode('utf-8'))

        swgohgg_ships_url = 'http://api.swgoh.gg/ships'
        goutils.log2("DBG", "Get data from " + swgohgg_ships_url)
        r = requests.get(swgohgg_ships_url, allow_redirects=True)
        list_ships = json.loads(r.content.decode('utf-8'))

        list_units = list_characters + list_ships

        swgohgg_img_url = ''
        for character in list_units:
            if character['base_id'] == character_id:
                swgohgg_img_url = character['image']

        if swgohgg_img_url == '':
            goutils.log2("ERR", "Cannot find image name for "+character_id)
        else:
            goutils.log2("INFO", "download portrait from swgoh.gg "+swgohgg_img_url)
            r = requests.get(swgohgg_img_url, allow_redirects=True)
            f = open(character_img_name, 'wb')
            f.write(r.content)
            f.close()
    
    try:
        char_img = Image.open(character_img_name)
    except OSError as e:
        goutils.log2("ERR", "cannot open image "+character_img_name)
        char_img = Image.new('RGBA', (128, 128), (0,0,0,0))

    char_img = char_img.resize((128,128))
    return char_img

def get_guild_logo(dict_guild, target_size):
    logo_name = dict_guild["profile"]["bannerLogoId"]
    logo_colors = dict_guild["profile"]["bannerColorId"]

    logo_color_elements = logo_colors.split("_")
    if logo_colors.startswith("bright"):
        color1 = "bright_" + logo_color_elements[1]
        color2 = "_".join(logo_color_elements[2:])
    else:
        color1 = logo_color_elements[0]
        color2 = "_".join(logo_color_elements[1:])

    if color1 in dict_colors:
        rgb1 = dict_colors[color1]
    else:
        rgb1 = (255, 255, 255)
        goutils.log("WAR", "get_guild_logo", "unknown color "+color1)
    rgb1_dark = tuple([int(x/2) for x in rgb1])

    if color2 in dict_colors:
        rgb2 = dict_colors[color2]
    else:
        rgb2 = (0, 0, 0)
        goutils.log("WAR", "get_guild_logo", "unknown color "+color2)

    logo_img_name = 'IMAGES'+os.path.sep+'GUILD_LOGOS'+os.path.sep+logo_name+'.png'
    if not os.path.exists(logo_img_name):
        url = 'https://swgoh.gg/static/img/assets/tex.' + logo_name + ".png"
        goutils.log("INFO", "get_guild_logo", "download guild logo from swgoh.gg "+url)
        r = requests.get(url, allow_redirects=True)
        f = open(logo_img_name, 'wb')
        f.write(r.content)
        f.close()
    
    image = Image.new('RGBA', (128, 128), (0,0,0,0))
    image_draw = ImageDraw.Draw(image)

    #Draw background circle with color2
    image_draw.ellipse((2,2,126,126), fill=rgb2)

    #Add guild image in foreground with color1
    logo_img = Image.open(logo_img_name)
    logo_img = logo_img.convert("RGBA")
    logo_img = replace_color(logo_img, (0, 0, 0), rgb1_dark)

    #Add edges
    logo_edges = logo_img.filter(ImageFilter.FIND_EDGES)
    logo_edges = replace_color(logo_edges, (0, 0, 0), rgb1)

    #mask_image = Image.open('IMAGES'+os.path.sep+'PORTRAIT_FRAME'+os.path.sep+'mask-circle-128.png')
    image.paste(logo_img, (0, 0), logo_img)
    image.paste(logo_edges, (0, 0), logo_edges)

    image = image.resize(target_size)
    return image

def replace_color(img, c1, c2):
    datas = img.getdata()

    new_image_data = []
    for item in datas:
        # change all white (also shades of whites) pixels to yellow
        if item[0:3] == c1:
            if len(item) == 4:
                new_image_data.append((c2[0], c2[1], c2[2], item[3]))
            else:
                new_image_data.append(c2)
        else:
            new_image_data.append(item)
                                              
    # update image data
    img.putdata(new_image_data)

    return img

def add_vertical(img1, img2):
    if img1 == None:
        return img2
    elif img2 == None:
        return img1

    w1, h1 = img1.size
    w2, h2 = img2.size
    image = Image.new('RGB', (max(w1, w2), h1+h2), (0,0,0))
    image.paste(img1, (0, 0))
    image.paste(img2, (0, h1))

    return image
    
def add_horizontal(img1, img2):
    if img1 == None:
        return img2
    elif img2 == None:
        return img1

    w1, h1 = img1.size
    w2, h2 = img2.size
    image = Image.new('RGB', (w1+w2, max(h1,h2)), (0,0,0))
    image.paste(img1, (0, 0))
    image.paste(img2, (w1, 0))

    return image
    
def get_image_from_character(character_id, dict_player, game_mode):
    dict_unitsList = data.get("unitsList_dict.json")
    dict_capas = data.get("unit_capa_list.json")

    portrait_image = Image.new('RGB', (PORTRAIT_SIZE, PORTRAIT_SIZE), (0,0,0))
    portrait_draw = ImageDraw.Draw(portrait_image)
    
    #Get basic image of character
    character_image = get_image_from_id(character_id)
    character_mask_image = Image.open('IMAGES'+os.path.sep+'PORTRAIT_FRAME'+os.path.sep+'mask-circle-128.png')
    portrait_image.paste(character_image, (20, 10), character_mask_image)
    
    #Get character details
    if character_id in dict_player["rosterUnit"]:
        character = dict_player["rosterUnit"][character_id]

        #RARITY
        rarity = character["currentRarity"]
        active_star_img = Image.open('IMAGES'+os.path.sep+'PORTRAIT_FRAME'+os.path.sep+'star.png')
        inactive_star_img = Image.open('IMAGES'+os.path.sep+'PORTRAIT_FRAME'+os.path.sep+'star-inactive.png')
        for cur_rarity in [1, 2, 3, 4, 5, 6, 7]:
            pos_x = cur_rarity*21 - 10
            pos_y = 140
            if rarity >= cur_rarity:
                star_image = active_star_img
            else:
                star_image = inactive_star_img
            portrait_image.paste(star_image, (pos_x, pos_y), star_image)

        combatType = dict_unitsList[character_id]["combatType"]
        forceAlignment = dict_unitsList[character_id]["forceAlignment"]

        if combatType == 1:
            #GEAR
            gear = character["currentTier"]
            if gear < 13:
                gear_frame_img = Image.open('IMAGES'+os.path.sep+'PORTRAIT_FRAME'+os.path.sep+'g'+str(gear)+'-frame.png')
                gear_frame_img = gear_frame_img.resize((126,126))
                portrait_image.paste(gear_frame_img, (21, 11), gear_frame_img)
            else:
                gear_frame_img = Image.open('IMAGES'+os.path.sep+'PORTRAIT_FRAME'+os.path.sep+'g13-frame-atlas.png')
                if forceAlignment == 2:
                    gear_frame_img = gear_frame_img.crop((0, 0, 120, 112))
                elif forceAlignment == 3:
                    gear_frame_img = gear_frame_img.crop((0, 112, 120, 224))
                else:
                    gear_frame_img = gear_frame_img.crop((0, 224, 120, 336))
                gear_frame_img = gear_frame_img.resize((148,148))
                portrait_image.paste(gear_frame_img, (11, 1), gear_frame_img)

            #RELIC
            relic = character["relic"]["currentTier"]-2
            if relic>0:
                relic_frame_img = Image.open('IMAGES'+os.path.sep+'PORTRAIT_FRAME'+os.path.sep+'relic-badge-atlas.png')

                if forceAlignment == 2:
                    relic_frame_img = relic_frame_img.crop((0, 0, 54, 54))
                elif forceAlignment == 3:
                    relic_frame_img = relic_frame_img.crop((0, 54, 54, 108))
                else:
                    relic_frame_img = relic_frame_img.crop((0, 108, 54, 162))
                relic_frame_img = relic_frame_img.resize((70,70))
                portrait_image.paste(relic_frame_img, (50, 87), relic_frame_img)
                portrait_draw.text((78,107), str(relic), (255, 255, 255), font=font)
            else:
                #LEVEL
                level = character["currentLevel"]
                level_frame_img = Image.open('IMAGES'+os.path.sep+'PORTRAIT_FRAME'+os.path.sep+'level-badge.png')
                level_frame_img = level_frame_img.resize((40,40))
                portrait_image.paste(level_frame_img, (64, 107), level_frame_img)
                portrait_draw.text((86-8*len(str(level)),112), str(level), (255, 255, 255), font=font)

            #ZETAS
            zetas = 0
            for skill in character["skill"]:
                skill_id = skill["id"]
                if ( (skill["tier"]+2) >= dict_capas[character_id][skill_id]["zetaTier"] ):
                    zetas += 1
            if zetas != None and zetas>0:
                zeta_frame_img = Image.open('IMAGES'+os.path.sep+'PORTRAIT_FRAME'+os.path.sep+'tex.skill_zeta_glow.png')
                zeta_frame_img = zeta_frame_img.resize((60,60))
                portrait_image.paste(zeta_frame_img, (5, 85), zeta_frame_img)
                portrait_draw.text((29,100), str(zetas), (255, 255, 255), font=font)

            #OMICRONS
            omicrons = 0
            if character_id in dict_capas:
                for skill in character["skill"]:
                    skill_id = skill['id']
                    skill_tier = skill['tier']+2
                    if skill_id in dict_capas[character_id]:
                        if skill_tier >= dict_capas[character_id][skill_id]["omicronTier"]:
                            if game_mode=="" or (dict_capas[character_id][skill_id]["omicronMode"]==game_mode):
                                omicrons += 1
            if omicrons>0:
                omicron_frame_img = Image.open('IMAGES'+os.path.sep+'PORTRAIT_FRAME'+os.path.sep+'tex.skill_omicron.png')
                omicron_frame_img = omicron_frame_img.resize((60,60))
                portrait_image.paste(omicron_frame_img, (106, 85), omicron_frame_img)
                portrait_draw.text((130,100), str(omicrons), (255, 255, 255), font=font)
        else:
            #LEVEL
            level = character["currentLevel"]
            level_frame_img = Image.open('IMAGES'+os.path.sep+'PORTRAIT_FRAME'+os.path.sep+'level-badge.png')
            level_frame_img = level_frame_img.resize((40,40))
            portrait_image.paste(level_frame_img, (4, 107), level_frame_img)
            portrait_draw.text((26-8*len(str(level)),112), str(level), (255, 255, 255), font=font)

            #CREW
            if "crew" in dict_unitsList[character_id] and dict_unitsList[character_id]["crew"]!= None:
                for crew_element in dict_unitsList[character_id]["crew"]:
                    crew_id = crew_element["unitId"]
                    crew_image = get_image_from_character(crew_id, dict_player, game_mode)
                    portrait_image = add_vertical(portrait_image, crew_image)

        #Orange frame if character unavail
        if 'reserved' in character:
            if character['reserved']:
                orange_img = Image.new('RGB', (PORTRAIT_SIZE, PORTRAIT_SIZE), 'orange')
                portrait_image = Image.blend(portrait_image, orange_img, 0.5)
    else:
        #character is invalid, display it in reduce
        red_img = Image.new('RGB', (PORTRAIT_SIZE, PORTRAIT_SIZE), 'red')
        portrait_image = Image.blend(portrait_image, red_img, 0.5)

    return portrait_image

#################################################
# get_image_from_team
# list_character_ids: [toon1_ID, toon2_ID, ...], dict_player, 
# dict_player: roster of the player
# tw_territory: 'T1', 'T2', 'F1', ...
#################################################
def get_image_from_team(list_character_ids, dict_player, tw_territory, game_mode):
    list_portrait_images = []
    print(str(dict_player)[:1000])
    player_name = dict_player["name"]

    total_gp = 0
    for character_id in list_character_ids:
        if character_id in dict_player["rosterUnit"]:
            total_gp += dict_player["rosterUnit"][character_id]["gp"]
        character_img = get_image_from_character(character_id, dict_player, game_mode)
        list_portrait_images.append(character_img)

    if tw_territory != '':
        tw_img = Image.open('IMAGES'+os.path.sep+'TW'+os.path.sep+tw_territory+'.png')
        tw_img.resize((120, 120))
        tw_portrait_image = Image.new('RGB', (PORTRAIT_SIZE, PORTRAIT_SIZE), (0,0,0))
        tw_portrait_image.paste(tw_img, (24, 24))
        list_portrait_images = [tw_portrait_image] + list_portrait_images

    image_all_portraits = None
    while len(list_portrait_images) > 0:
        line_image = None
        for img in list_portrait_images[:MAX_WIDTH_PORTRAITS]:
            line_image = add_horizontal(line_image, img)
        w, h = line_image.size
        line_image_draw = ImageDraw.Draw(line_image)
        line_image_draw.line([(0,0),(w,0)], fill="white", width=0)
        image_all_portraits = add_vertical(image_all_portraits, line_image)
        if len(list_portrait_images) > MAX_WIDTH_PORTRAITS:
            empty_portrait_image = Image.new('RGB', (PORTRAIT_SIZE, PORTRAIT_SIZE), (0,0,0))
            list_portrait_images = [empty_portrait_image] + list_portrait_images[MAX_WIDTH_PORTRAITS:]
        else:
            list_portrait_images = []

    complete_player_name = player_name + " - " + str(total_gp)
    w_txt, h_txt = font.getsize(complete_player_name)
    name_img = Image.new('RGB', (w_txt+20, NAME_HEIGHT), (0,0,0))
    name_draw = ImageDraw.Draw(name_img)
    name_draw.text((10,5), complete_player_name, (255, 255, 255), font=font)

    team_img = add_vertical(name_img, image_all_portraits)

    return team_img

#######################
def get_result_image_from_images(img1_url, img1_size, img2_url, img2_sizes, idx_img2):
    img1 = Image.open(requests.get(img1_url, stream=True).raw)
    w1, h1 = img1.size
    img2 = Image.open(requests.get(img2_url, stream=True).raw)
    w2, h2 = img2.size

    
    #Get attacker team
    attacker_img = img1.crop((0, 0, w1, img1_size))
    
    #Get defender team / remove the letter before the name
    img2_top = sum(img2_sizes[:idx_img2])
    img2_bottom = sum(img2_sizes[:idx_img2+1])
    defender_img = img2.crop((0, img2_top, w2, img2_bottom))

    #Merge images
    result_image = add_vertical(attacker_img, defender_img)

    return result_image
