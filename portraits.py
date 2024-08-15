import requests
import os
import math
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import json
import io

import goutils
import data

font8 = ImageFont.truetype("IMAGES"+os.path.sep+"arial.ttf", 8)
font12 = ImageFont.truetype("IMAGES"+os.path.sep+"arial.ttf", 12)
font24 = ImageFont.truetype("IMAGES"+os.path.sep+"arial.ttf", 24)

NAME_HEIGHT = 30
PORTRAIT_SIZE = 168
MAX_WIDTH_PORTRAITS = 10

# list recovered from gamedata.json / 24 / 2
dict_colors = { "bright_orange_brown": ["0xFFCA52FF", "0x5C2C1AFF"],
                "bright_blue_dark_blue": ["0xA4DCFFFF", "0x0020BFFF"],
                "white_red": ["0xFFFFFFFF", "0x430000FF"],
                "cyan_purple": ["0x00D4FFFF", "0x880084FF"],
                "gold_purple": ["0xF7C419FF", "0x542583FF"],
                "green_blue": ["0x05FF9CFF", "0x1A427DFF"],
                "red_white": ["0xEB2429FF", "0xEAE4D6FF"],
                "green_dark_green": ["0xC6FA08FF", "0x283E04FF"]
              }
reverse_guild_logos = ['guild_icon_senate', 
                       'guild_icon_flame',
                       'guild_icon_cis',
                       'guild_icon_triangle',
                       'guild_icon_mandalorian']

def get_image_from_id(character_id):
    character_img_name = 'IMAGES'+os.path.sep+'CHARACTERS'+os.path.sep+character_id+'.png'
    if not os.path.exists(character_img_name):
        swgohgg_characters_url = 'https://swgoh.gg/api/characters'
        goutils.log2("DBG", "Get data from " + swgohgg_characters_url)
        r = requests.get(swgohgg_characters_url, allow_redirects=True)
        #print(r.content[:200])
        list_characters = json.loads(r.content.decode('utf-8'))

        swgohgg_ships_url = 'https://swgoh.gg/api/ships'
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

    if logo_colors in dict_colors:
        rgb1_txt = dict_colors[logo_colors][0]
        rgb1 = (int(rgb1_txt[2:4], 16),
                int(rgb1_txt[4:6], 16),
                int(rgb1_txt[6:8], 16))
        rgb2_txt = dict_colors[logo_colors][1]
        rgb2 = (int(rgb2_txt[2:4], 16),
                int(rgb2_txt[4:6], 16),
                int(rgb2_txt[6:8], 16))
    else:
        rgb1 = (255, 255, 255)
        rgb2 = (0, 0, 0)
        goutils.log2("WAR", "unknown color "+logo_colors)
    rgb1_dark = tuple([int(x/2) for x in rgb1])
    rgb2_dark = tuple([int(x/2) for x in rgb2])

    logo_img_name = 'IMAGES'+os.path.sep+'GUILD_LOGOS'+os.path.sep+logo_name+'.png'
    if not os.path.exists(logo_img_name):
        #url = 'https://swgoh.gg/static/img/assets/tex.' + logo_name + ".png"
        url = 'https://game-assets.swgoh.gg/textures/tex.' + logo_name + ".png"
        goutils.log("INFO", "get_guild_logo", "download guild logo from swgoh.gg "+url)
        r = requests.get(url, allow_redirects=True)
        f = open(logo_img_name, 'wb')
        f.write(r.content)
        f.close()
    
    image = Image.new('RGBA', (128, 128), (0,0,0,0))
    image_draw = ImageDraw.Draw(image)

    #Draw background circle with color2
    if logo_name in reverse_guild_logos:
        image_draw.ellipse((2,2,126,126), fill=rgb1_dark)
    else:
        image_draw.ellipse((2,2,126,126), fill=rgb2)

    #Add guild image in foreground with color1
    logo_img = Image.open(logo_img_name)
    logo_img = logo_img.convert("RGBA")
    if logo_name in reverse_guild_logos:
        logo_img = replace_color(logo_img, (0, 0, 0), rgb2)
    else:
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

#Add img2 under img1
def add_vertical(img1, img2):
    if img1 == None:
        return img2
    elif img2 == None:
        return img1

    w1, h1 = img1.size
    w2, h2 = img2.size
    image = Image.new('RGBA', (max(w1, w2), h1+h2), (0,0,0))
    image.paste(img1, (0, 0))
    image.paste(img2, (0, h1))

    return image
    
#Add img2 at the right of img1
def add_horizontal(img1, img2):
    if img1 == None:
        return img2
    elif img2 == None:
        return img1

    w1, h1 = img1.size
    w2, h2 = img2.size
    image = Image.new('RGBA', (w1+w2, max(h1,h2)), (0,0,0))
    image.paste(img1, (0, 0))
    image.paste(img2, (w1, 0))

    return image
    
def get_image_from_defId(character_id, dict_player, game_mode):
    dict_unitsList = data.get("unitsList_dict.json")

    #Get character details
    if character_id in dict_player["rosterUnit"]:
        character = dict_player["rosterUnit"][character_id]

        #CREW
        crew_units = []
        if "crew" in dict_unitsList[character_id] and dict_unitsList[character_id]["crew"]!= None:
            for crew_element in dict_unitsList[character_id]["crew"]:
                crew_id = crew_element["unitId"]
                crew_units.append(dict_player["rosterUnit"][crew_id])

    else:
        character = {"definitionId": character_id, "locked": True}

    portrait_image = get_image_from_unit(character, crew_units, game_mode)
    return portrait_image

########################################
# IN: character: unit as an element of rosterUnit
# IN: crew_units: table of units as an element of rosterUnit, only for ships
# IN: game_mode: string used to display omicrons (CQ, GA, GA3, GA5, RD, TB, TW)
########################################
def get_image_from_unit(character, crew_units, game_mode):
    dict_unitsList = data.get("unitsList_dict.json")
    dict_capas = data.get("unit_capa_list.json")

    portrait_image = Image.new('RGBA', (PORTRAIT_SIZE, PORTRAIT_SIZE), (0,0,0))
    portrait_draw = ImageDraw.Draw(portrait_image)
    
    #Get basic image of character
    character_id = character["definitionId"].split(':')[0]
    character_image = get_image_from_id(character_id)
    character_mask_image = Image.open('IMAGES'+os.path.sep+'PORTRAIT_FRAME'+os.path.sep+'mask-circle-128.png')
    portrait_image.paste(character_image, (20, 10), character_mask_image)
    
    if "locked" in character and character["locked"]:
        #character is invalid, display it in red
        red_img = Image.new('RGBA', (PORTRAIT_SIZE, PORTRAIT_SIZE), 'red')
        portrait_image = Image.blend(portrait_image, red_img, 0.5)
        return portrait_image

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

            #FIRST LOOK IF ULTIMATE ACTIVATED
            ultimate = False
            if "purchaseAbilityId" in character:
                for ability in character["purchaseAbilityId"]:
                    if ability.startswith("ultimateability"):
                        ultimate = True

            #ALLOCATE the right relic badge depending on ultimate, then alignment if no ultimate
            if ultimate:
                relic_frame_img = relic_frame_img.crop((0, 162, 54, 216))
            elif forceAlignment == 2:
                relic_frame_img = relic_frame_img.crop((0, 0, 54, 54))
            elif forceAlignment == 3:
                relic_frame_img = relic_frame_img.crop((0, 54, 54, 108))
            else:
                relic_frame_img = relic_frame_img.crop((0, 108, 54, 162))
            relic_frame_img = relic_frame_img.resize((70,70))
            portrait_image.paste(relic_frame_img, (50, 87), relic_frame_img)
            portrait_draw.text((78,107), str(relic), (255, 255, 255), font=font24)
        else:
            #LEVEL
            level = character["currentLevel"]
            level_frame_img = Image.open('IMAGES'+os.path.sep+'PORTRAIT_FRAME'+os.path.sep+'level-badge.png')
            level_frame_img = level_frame_img.resize((40,40))
            portrait_image.paste(level_frame_img, (64, 107), level_frame_img)
            portrait_draw.text((86-8*len(str(level)),112), str(level), (255, 255, 255), font=font24)

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
            portrait_draw.text((29,100), str(zetas), (255, 255, 255), font=font24)

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
            portrait_draw.text((130,100), str(omicrons), (255, 255, 255), font=font24)
    else:
        #LEVEL
        level = character["currentLevel"]
        level_frame_img = Image.open('IMAGES'+os.path.sep+'PORTRAIT_FRAME'+os.path.sep+'level-badge.png')
        level_frame_img = level_frame_img.resize((40,40))
        portrait_image.paste(level_frame_img, (4, 107), level_frame_img)
        portrait_draw.text((26-8*len(str(level)),112), str(level), (255, 255, 255), font=font24)

        #CREW
        for crew_unit in crew_units:
            #for crew image, the game_mode is ignored as it serves to display omicrons
            crew_image = get_image_from_unit(crew_unit, None, "")
            portrait_image = add_vertical(portrait_image, crew_image)

    #Orange frame if character unavail
    # Unavail character is tagged with "reserved" and it is applicable with game_mode="TW" only
    # This to prevent displaying a crew in orange because the crew is in defense
    # Display of crew is always done with game_mode=""
    if 'reserved' in character and game_mode=="TW":
        if character['reserved']:
            orange_img = Image.new('RGBA', (PORTRAIT_SIZE, PORTRAIT_SIZE), 'orange')
            portrait_image = Image.blend(portrait_image, orange_img, 0.5)

    return portrait_image

#################################################
# get_image_from_defIds
# list_character_ids: [toon1_ID, toon2_ID, ...], dict_player, 
# dict_player: roster of the player
# tw_territory: 'T1', 'T2', 'F1', ...
#################################################
def get_image_from_defIds(list_character_ids, dict_player, tw_territory, omicron_mode):
    dict_unitsList = data.get("unitsList_dict.json")

    player_name = dict_player["name"]

    list_units = []
    for character_id in list_character_ids:
        if character_id in dict_player["rosterUnit"]:
            unit = dict_player["rosterUnit"][character_id]

            #CREW
            crew_units = []
            if "crew" in dict_unitsList[character_id] and dict_unitsList[character_id]["crew"]!= None:
                for crew_element in dict_unitsList[character_id]["crew"]:
                    crew_id = crew_element["unitId"]
                    crew_units.append(dict_player["rosterUnit"][crew_id])
        else:
            unit = {"definitionId": character_id, "locked": True}
            crew_units = []

        list_units.append({"unit": unit, "crew": crew_units})

    return get_image_from_units(list_units, player_name, 
                                tw_territory=tw_territory, 
                                omicron_mode=omicron_mode)

def get_image_from_units(list_characters, player_name, tw_territory="", omicron_mode="", team_gp=None):
    list_portrait_images = []

    total_gp = 0
    for unit_crew in list_characters:
        character = unit_crew["unit"]
        crew = unit_crew["crew"]
        if "locked" in character and character["locked"]:
            # no impact on GP
            pass
        elif "gp" in character:
            total_gp += character["gp"]

        character_img = get_image_from_unit(character, crew, omicron_mode)
        list_portrait_images.append(character_img)

    if team_gp != None:
        total_gp = team_gp

    if tw_territory != '':
        tw_img = Image.open('IMAGES'+os.path.sep+'TW'+os.path.sep+tw_territory+'.png')
        tw_img.resize((120, 120))
        tw_portrait_image = Image.new('RGBA', (PORTRAIT_SIZE, PORTRAIT_SIZE), (0,0,0))
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
            empty_portrait_image = Image.new('RGBA', (PORTRAIT_SIZE, PORTRAIT_SIZE), (0,0,0))
            list_portrait_images = [empty_portrait_image] + list_portrait_images[MAX_WIDTH_PORTRAITS:]
        else:
            list_portrait_images = []

    complete_player_name = player_name + " - " + str(total_gp)
    w_txt, h_txt = font24.getsize(complete_player_name)
    name_img = Image.new('RGBA', (w_txt+20, NAME_HEIGHT), (0,0,0))
    name_draw = ImageDraw.Draw(name_img)
    name_draw.text((10,5), complete_player_name, (255, 255, 255), font=font24)

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

def get_image_from_eqpt_id(eqpt_id):
    dict_eqpt = data.get("eqpt_dict.json")
    dict_tier_color = {0: "#000000", 
                       1: "#97d2d3", 
                       2: "#aff65b",
                       4: "#51bcf6",
                       7: "#844df1",
                       9: "#844df1",
                       11: "#844df1",
                       12: "#f1c752"}

    eqpt_img_name = 'IMAGES'+os.path.sep+'EQUIPMENT'+os.path.sep+eqpt_id+'.png'
    if not os.path.exists(eqpt_img_name):
        eqpt_asset_id = dict_eqpt[eqpt_id]["iconKey"]
        if "tier" in dict_eqpt[eqpt_id]:
            eqpt_tier = dict_eqpt[eqpt_id]["tier"]
        else:
            eqpt_tier = 0
        if "mark" in dict_eqpt[eqpt_id]:
            eqpt_mk = dict_eqpt[eqpt_id]["mark"]
        else:
            eqpt_mk = ""
        swgohgg_img_url = "https://game-assets.swgoh.gg/textures/" + eqpt_asset_id + ".png"
        goutils.log2("INFO", "download equipment image from swgoh.gg "+swgohgg_img_url)
        r = requests.get(swgohgg_img_url, allow_redirects=True)
        img = Image.open(io.BytesIO(r.content))
        img = img.resize((34,34)) #should not be useful, but safety net

        #Create background with color of the tier
        colored_eqpt = Image.new("RGBA", (40,40), dict_tier_color[eqpt_tier])

        #put gear image in the center
        colored_eqpt.paste(img, (3, 3))
        img_draw = ImageDraw.Draw(colored_eqpt)

        #put Mk at top right
        mk_size = font8.getsize(eqpt_mk)
        img_draw.text((5+40/2-mk_size[0]/2, 5+3), eqpt_mk, (255, 255, 255), font=font8)

        # Save colored gear
        colored_eqpt.save(eqpt_img_name)

    else:
        colored_eqpt = Image.open(eqpt_img_name)

    return colored_eqpt

def get_image_from_eqpt_count(eqpt_id, needed_count, owned=None):
    dict_eqpt = data.get("eqpt_dict.json")
    FRE_FR = data.get("FRE_FR.json")

    image = Image.new('RGBA', (400, 50), (0,0,0))
    image_draw = ImageDraw.Draw(image)

    # PASTE (image, position, mask)
    image.paste(get_image_from_eqpt_id(eqpt_id), (5,5), get_image_from_eqpt_id(eqpt_id))
    eqpt_nameKey = dict_eqpt[eqpt_id]["nameKey"]
    eqpt_name = FRE_FR[eqpt_nameKey]
    eqpt_words = eqpt_name.split(" ")

    line_size = 0
    MAX_LINE_SIZE=200
    txt_lines = []
    cur_line = eqpt_words[0]
    for word in eqpt_words[1:]:
        if font12.getsize(cur_line+" "+word)[0] < MAX_LINE_SIZE:
            cur_line += " " + word
        else:
            txt_lines.append(cur_line)
            cur_line = word
    txt_lines.append(cur_line)

    line_height = font12.getsize(cur_line)[1]
    image_draw.text((50,25-(len(txt_lines)*line_height)/2), "\n".join(txt_lines), (255, 255, 255), font=font12)

    if owned!=None:
        #needed and owned
        image_draw.text((50+MAX_LINE_SIZE+20, 25-line_height), str(needed_count)+" ("+str(owned)+")", (255, 255, 255), font=font12)

        #Need to farm
        image_draw.text((50+MAX_LINE_SIZE+70, 25-line_height), "> "+str(max(0,needed_count-owned)), (255, 255, 255), font=font12)
    else:
        image_draw.text((50+MAX_LINE_SIZE+20, 25-line_height), str(needed_count), (255, 255, 255), font=font12)

    # Farm locations
    farm_locations = ""
    if "lookupMission" in dict_eqpt[eqpt_id]:
        for mission in dict_eqpt[eqpt_id]["lookupMission"]:
            #print(mission)
            cId = mission["missionIdentifier"]["campaignId"]
            if cId.startswith("C01"):
                if cId[3:] == "L":
                    mission_farm = "LS-"
                elif cId[3:] == "D":
                    mission_farm = "DS-"
                else: #SP
                    mission_farm = "FL-"

                cDifficulty = mission["missionIdentifier"]["campaignNodeDifficulty"]
                mission_farm += cDifficulty[0]

                cMapId = mission["missionIdentifier"]["campaignMapId"]
                mission_farm += cMapId[-1]

                cMissionId = mission["missionIdentifier"]["campaignMissionId"]
                mission_farm += "ABCDEFGHIJKL"[int(cMissionId[-2:])-1]
                #print(mission_farm)

                farm_locations += mission_farm + " "

    image_draw.text((50+MAX_LINE_SIZE+20, 25), farm_locations, (255, 255, 255), font=font12)

    return image

def get_image_from_eqpt_list(eqpt_list, display_owned=False):
    list_eqpt_images = []
    for eqpt in eqpt_list:
        if display_owned:
            if eqpt[1]>eqpt[2]:
                img = get_image_from_eqpt_count(eqpt[0], eqpt[1], owned=eqpt[2])
            else:
                img = None
        else:
            img = get_image_from_eqpt_count(eqpt[0], eqpt[1])

        if img!=None:
            list_eqpt_images.append(img)

    eqpt_list_img = list_eqpt_images[0]
    for img in list_eqpt_images[1:]:
        eqpt_list_img = add_vertical(eqpt_list_img, img)

    return eqpt_list_img
