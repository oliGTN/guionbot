import requests
import os
import math
from PIL import Image, ImageDraw, ImageFont

def get_image_from_id(character_id):
    character_img_name = 'IMAGES'+os.path.sep+'CHARACTERS'+os.path.sep+character_id+'.png'
    if not os.path.exists(character_img_name):
        url = 'https://swgoh.gg/game-asset/u/' + character_id
        print("INFO: download portrait from swgoh.gg "+url)
        r = requests.get(url, allow_redirects=True)
        f = open(character_img_name, 'wb')
        f.write(r.content)
        f.close()
    
    char_img = Image.open(character_img_name)
    char_img = char_img.resize((128,128))
    return char_img
    
def get_image_from_character(character_id, force_alignment, rarity, level, gear, relic, zetas, combatType):
    portrait_image = Image.new('RGB', (168, 168), (0,0,0))
    portrait_draw = ImageDraw.Draw(portrait_image)
    font = ImageFont.truetype("IMAGES"+os.path.sep+"arial.ttf", 24)
    
    character_image = get_image_from_id(character_id)
    character_mask_image = Image.open('IMAGES'+os.path.sep+'PORTRAIT FRAME'+os.path.sep+'mask-circle-128.png')
    portrait_image.paste(character_image, (20, 20), character_mask_image)
    
    if force_alignment != 0:
        if combatType == 1:
            # GEAR
            if gear < 13:
                gear_frame_img = Image.open('IMAGES'+os.path.sep+'PORTRAIT FRAME'+os.path.sep+'g'+str(gear)+'-frame.png')
                gear_frame_img = gear_frame_img.resize((126,126))
                portrait_image.paste(gear_frame_img, (21, 21), gear_frame_img)
            else:
                gear_frame_img = Image.open('IMAGES'+os.path.sep+'PORTRAIT FRAME'+os.path.sep+'g13-frame-atlas.png')
                if force_alignment == 2:
                    gear_frame_img = gear_frame_img.crop((0, 0, 120, 112))
                else:
                    gear_frame_img = gear_frame_img.crop((0, 112, 120, 224))
                gear_frame_img = gear_frame_img.resize((148,148))
                portrait_image.paste(gear_frame_img, (11, 11), gear_frame_img)
                
            # RELIC
            if relic>0:
                relic_frame_img = Image.open('IMAGES'+os.path.sep+'PORTRAIT FRAME'+os.path.sep+'relic-badge-atlas.png')
                if force_alignment == 2:
                    relic_frame_img = relic_frame_img.crop((0, 0, 54, 54))
                else:
                    relic_frame_img = relic_frame_img.crop((0, 54, 54, 108))
                relic_frame_img = relic_frame_img.resize((70,70))
                portrait_image.paste(relic_frame_img, (100, 90), relic_frame_img)
                portrait_draw.text((128,110), str(relic), (255, 255, 255), font=font)
        
        # RARITY
        active_star_img = Image.open('IMAGES'+os.path.sep+'PORTRAIT FRAME'+os.path.sep+'star.png')
        inactive_star_img = Image.open('IMAGES'+os.path.sep+'PORTRAIT FRAME'+os.path.sep+'star-inactive.png')
        for cur_rarity in [1, 2, 3, 4, 5, 6, 7]:
            angle_deg = 90+4*20 - 20*cur_rarity
            pos_x = int(84 + 75*math.cos(angle_deg * math.pi / 180))-11
            pos_y = int(84 - 75*math.sin(angle_deg * math.pi / 180))-11
            if rarity >= cur_rarity:
                star_image = active_star_img
            else:
                star_image = inactive_star_img
            portrait_image.paste(star_image, (pos_x, pos_y), star_image)
        
        # LEVEL
        level_frame_img = Image.open('IMAGES'+os.path.sep+'PORTRAIT FRAME'+os.path.sep+'level-badge.png')
        level_frame_img = level_frame_img.resize((40,40))
        portrait_image.paste(level_frame_img, (64, 120), level_frame_img)
        portrait_draw.text((86-8*len(str(level)),125), str(level), (255, 255, 255), font=font)
        
        if combatType == 1:
            # ZETAS
            if zetas>0:
                zeta_frame_img = Image.open('IMAGES'+os.path.sep+'PORTRAIT FRAME'+os.path.sep+'tex.skill_zeta_glow.png')
                zeta_frame_img = zeta_frame_img.resize((60,60))
                portrait_image.paste(zeta_frame_img, (5, 95), zeta_frame_img)
                portrait_draw.text((29,110), str(zetas), (255, 255, 255), font=font)
    
    else:
        #character is invalid, display it in reduce
        red_img = Image.new('RGB', (168, 168), 'red')
        portrait_image = Image.blend(portrait_image, red_img, 0.5)
        
    return portrait_image

def get_image_from_team(list_character_ids, db_data):
    list_portrait_images = []

    for character_id in list_character_ids:
        character_data = [line for line in db_data if line[0] == character_id]
        if len(character_data) > 0:
            rarity = character_data[0][1]
            level = character_data[0][2]
            gear = character_data[0][3]
            relic = character_data[0][4]-2
            force_alignment = character_data[0][5]
            zetas = character_data[0][6]
            combatType = character_data[0][7]
        
            character_img = get_image_from_character(character_id,
                                                    force_alignment,
                                                    rarity, 
                                                    level, 
                                                    gear, 
                                                    relic, 
                                                    zetas,
                                                    combatType)
                
        else:
            #the character is not in the db_data
            character_img = get_image_from_character(character_id,
                                                    0,0,0,0,0,0,0)
                                                    
        list_portrait_images.append(character_img)
        
    team_img = Image.new('RGB', (168*len(list_portrait_images), 168), (0,0,0))
    x=0
    for img in list_portrait_images:
        team_img.paste(img, (x, 0))
        x+=168
    
    return team_img

    