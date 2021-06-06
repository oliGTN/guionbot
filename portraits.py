import requests
import os
import math
from PIL import Image, ImageDraw, ImageFont

import goutils

font = ImageFont.truetype("IMAGES"+os.path.sep+"arial.ttf", 24)

NAME_HEIGHT = 30
PORTRAIT_SIZE = 168
MAX_WIDTH_PORTRAITS = 10

def get_image_from_id(character_id):
    character_img_name = 'IMAGES'+os.path.sep+'CHARACTERS'+os.path.sep+character_id+'.png'
    if not os.path.exists(character_img_name):
        url = 'https://swgoh.gg/game-asset/u/' + character_id + ".png"
        goutils.log("INFO", "get_image_from_id", "download portrait from swgoh.gg "+url)
        r = requests.get(url, allow_redirects=True)
        f = open(character_img_name, 'wb')
        f.write(r.content)
        f.close()
    
    char_img = Image.open(character_img_name)
    char_img = char_img.resize((128,128))
    return char_img

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
    
def get_image_from_character(character_id, dict_player, dict_unitsList):
    portrait_image = Image.new('RGB', (PORTRAIT_SIZE, PORTRAIT_SIZE), (0,0,0))
    portrait_draw = ImageDraw.Draw(portrait_image)
    
    #Get basic image of character
    character_image = get_image_from_id(character_id)
    character_mask_image = Image.open('IMAGES'+os.path.sep+'PORTRAIT_FRAME'+os.path.sep+'mask-circle-128.png')
    portrait_image.paste(character_image, (20, 20), character_mask_image)
    
    #Get character details
    if character_id in dict_player["roster"]:
        character = dict_player["roster"][character_id]

        #RARITY
        rarity = character["rarity"]
        active_star_img = Image.open('IMAGES'+os.path.sep+'PORTRAIT_FRAME'+os.path.sep+'star.png')
        inactive_star_img = Image.open('IMAGES'+os.path.sep+'PORTRAIT_FRAME'+os.path.sep+'star-inactive.png')
        for cur_rarity in [1, 2, 3, 4, 5, 6, 7]:
            angle_deg = 90+4*20 - 20*cur_rarity
            pos_x = int(84 + 75*math.cos(angle_deg * math.pi / 180))-11
            pos_y = int(84 - 75*math.sin(angle_deg * math.pi / 180))-11
            if rarity >= cur_rarity:
                star_image = active_star_img
            else:
                star_image = inactive_star_img
            portrait_image.paste(star_image, (pos_x, pos_y), star_image)

        #LEVEL
        level = character["level"]
        level_frame_img = Image.open('IMAGES'+os.path.sep+'PORTRAIT_FRAME'+os.path.sep+'level-badge.png')
        level_frame_img = level_frame_img.resize((40,40))
        portrait_image.paste(level_frame_img, (64, 120), level_frame_img)
        portrait_draw.text((86-8*len(str(level)),125), str(level), (255, 255, 255), font=font)

        combatType = character["combatType"]
        if character_id in dict_unitsList:
            forceAlignment = dict_unitsList[character_id]["forceAlignment"]
        else:
            goutils.log("WAR", "portraits.get_image_from_character", "unkonwn forceAlignment for "+character_id)
            forceAlignment = 1

        if combatType == 1:
            #GEAR
            gear = character["gear"]
            if gear < 13:
                gear_frame_img = Image.open('IMAGES'+os.path.sep+'PORTRAIT_FRAME'+os.path.sep+'g'+str(gear)+'-frame.png')
                gear_frame_img = gear_frame_img.resize((126,126))
                portrait_image.paste(gear_frame_img, (21, 21), gear_frame_img)
            else:
                gear_frame_img = Image.open('IMAGES'+os.path.sep+'PORTRAIT_FRAME'+os.path.sep+'g13-frame-atlas.png')
                if forceAlignment == 2:
                    gear_frame_img = gear_frame_img.crop((0, 0, 120, 112))
                else:
                    gear_frame_img = gear_frame_img.crop((0, 112, 120, 224))
                gear_frame_img = gear_frame_img.resize((148,148))
                portrait_image.paste(gear_frame_img, (11, 11), gear_frame_img)

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
                portrait_image.paste(relic_frame_img, (100, 90), relic_frame_img)
                portrait_draw.text((128,110), str(relic), (255, 255, 255), font=font)

            #ZETAS
            zetas = 0
            for skill in character["skills"]:
                if skill["isZeta"] and (skill["tier"]==skill["tiers"]):
                    zetas += 1
            if zetas != None and zetas>0:
                zeta_frame_img = Image.open('IMAGES'+os.path.sep+'PORTRAIT_FRAME'+os.path.sep+'tex.skill_zeta_glow.png')
                zeta_frame_img = zeta_frame_img.resize((60,60))
                portrait_image.paste(zeta_frame_img, (5, 95), zeta_frame_img)
                portrait_draw.text((29,110), str(zetas), (255, 255, 255), font=font)
        else:
            for crew_element in character["crew"]:
                crew_id = crew_element["unitId"]
                crew_image = get_image_from_character(crew_id, dict_player, dict_unitsList)
                portrait_image = add_vertical(portrait_image, crew_image)
    else:
        #character is invalid, display it in reduce
        red_img = Image.new('RGB', (PORTRAIT_SIZE, PORTRAIT_SIZE), 'red')
        portrait_image = Image.blend(portrait_image, red_img, 0.5)

    return portrait_image

#################################################
# get_image_from_team
# list_ids_allyCode: [toon1_ID, toon2_ID, ...], dict_player, 
# tw_territory: 'T1', 'T2', 'F1', ...
#################################################
def get_image_from_team(list_character_ids, dict_player, tw_territory, dict_unitsList):
    list_portrait_images = []
    player_name = dict_player["name"]

    total_gp = 0
    for character_id in list_character_ids:
        if character_id in dict_player["roster"]:
            total_gp += dict_player["roster"][character_id]["gp"]
        character_img = get_image_from_character(character_id, dict_player, dict_unitsList)
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
def get_result_image_from_images(img1_url, img2_url, idx_img2):
    img1 = Image.open(requests.get(img1_url, stream=True).raw)
    img2 = Image.open(requests.get(img2_url, stream=True).raw)

    result_width = 6 * PORTRAIT_SIZE
    result_image = Image.new('RGB', (result_width, 2*(NAME_HEIGHT+PORTRAIT_SIZE)), (0,0,0))
    
    #Get attacker team
    attacker_img = img1.crop((0, 0, result_width, NAME_HEIGHT + PORTRAIT_SIZE))
    
    #Get defender team / remove the letter before the name
    defender_img = img2.crop((0, idx_img2 * (NAME_HEIGHT + PORTRAIT_SIZE),
                            result_width, (idx_img2 + 1) * (NAME_HEIGHT + PORTRAIT_SIZE)))
    defender_name = defender_img.crop((40, 0, 6*PORTRAIT_SIZE, NAME_HEIGHT+5))
    defender_img.paste(defender_name, (0,0))


    #Merge images
    result_image.paste(attacker_img, (0, 0))
    result_image.paste(defender_img, (0, NAME_HEIGHT+PORTRAIT_SIZE))

    return result_image

def get_image_full_result(img_url, victory):
    img = Image.open(requests.get(img_url, stream=True).raw)

    #Get result icon
    if victory:
        result_icon = Image.open("IMAGES/ICONS/green_thumbup.png")
    else:
        result_icon = Image.open("IMAGES/ICONS/red_thumbdown.png")
    result_icon = result_icon.resize((120, 120))

    #Merge images
    img.paste(result_icon, (5*PORTRAIT_SIZE+24, NAME_HEIGHT+24), result_icon)

    return img

