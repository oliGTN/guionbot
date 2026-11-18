# PACKAGE imports
from discord.ext import commands
from discord import File
from discord import app_commands, Interaction
from discord import ui as discord_ui
from discord import ButtonStyle
from io import BytesIO

# BOT imports
import golog
import emojis

######################################
# basic functions mixing ctx and interactions
async def command_ack(ctx_interaction):
    msg = None
    if type(ctx_interaction) == commands.Context:
        ctx = ctx_interaction
        msg = await ctx.reply(emojis.thumb+" "+ctx.me.name+" réfléchit...")

    elif type(ctx_interaction) == Interaction:
        interaction = ctx_interaction
        await interaction.response.defer(thinking=True)
    else:
        print("In progress...")

    return msg

async def command_error(ctx_interaction, resp_msg, err_txt):
    if type(ctx_interaction) == commands.Context:
        ctx = ctx_interaction
        content = emojis.redcross+" "+err_txt

        await resp_msg.edit(content=content)

    elif type(ctx_interaction) == Interaction:
        interaction = ctx_interaction
        content = emojis.redcross+" "+err_txt

        try:
            await interaction.edit_original_response(content=content)
        except Exception as e:
            # Long-running commands may have deleted the deferred response or
            # outlived its 15-minute interaction webhook token.
            golog.log("WAR", "Unable to edit original interaction response: " + repr(e))
            await interaction.channel.send(content=content)

    else:
        print("ERROR "+err_txt)

async def command_ok(ctx_interaction, resp_msg, output_txt, images=None, files=None, intermediate=False):
    attachments = []

    if images != None:
        for image in images:
            with BytesIO() as image_binary:
                image.save(image_binary, 'PNG')
                image_binary.seek(0)
                attachments.append(File(fp=image_binary, filename='image.png'))

    if files != None:
        attachments += files

    if type(ctx_interaction) == commands.Context:
        golog.log("DBG", "context")
        if intermediate:
            content = emojis.hourglass+" "+output_txt
        else:
            content = emojis.check+" "+output_txt

        if attachments==[]:
            await resp_msg.edit(content=content)
        else:
            await resp_msg.edit(content=content, attachments=attachments)

    elif type(ctx_interaction) == Interaction:
        golog.log("DBG", "interaction")
        interaction = ctx_interaction
        if intermediate:
            content = emojis.hourglass+" "+output_txt
        else:
            content = emojis.check+" "+output_txt

        try:
            if attachments==[]:
                await interaction.edit_original_response(content=content)
            else:
                await interaction.edit_original_response(content=content, attachments=attachments)
        except Exception as e:
            # Long-running commands may have deleted the deferred response or
            # outlived its 15-minute interaction webhook token. Send the result
            # as a normal channel message instead.
            golog.log("WAR", "Unable to edit original interaction response: " + repr(e))
            send_kwargs = {"content": content}
            if attachments:
                send_kwargs["files"] = attachments
            await interaction.channel.send(**send_kwargs)

    else:
        if intermediate==False:
            content = "OK "+output_txt
        else:
            content = "In Progress... "+output_txt

        print(content)

        for attachment in attachments:
            print(attachment)

async def command_intermediate_to_ok(ctx_interaction, resp_msg, new_txt=None):
    if type(ctx_interaction) == commands.Context:
        ctx = ctx_interaction

        if new_txt == None:
            content = resp_msg.content.replace(emojis.hourglass, emojis.check)
        else:
            content = emojis.check+" "+new_txt

        await resp_msg.edit(content=content)

    elif type(ctx_interaction) == Interaction:
        interaction = ctx_interaction
        if new_txt == None:
            content = interaction.message.content.replace(emojis.hourglass, emojis.check)
        else:
            content = emojis.check+" "+new_txt
        await interaction.edit_original_response(content=content)

    else:
        if new_txt == None:
            print("OK")
        else:
            print("OK "+new_txt)

async def send_message(ctx_interaction, output_txt, images=None, files=None):
    attachments = []

    if images != None:
        for image in images:
            with BytesIO() as image_binary:
                image.save(image_binary, 'PNG')
                image_binary.seek(0)
                attachments.append(File(fp=image_binary, filename='image.png'))

    if files != None:
        attachments += files

    if ctx_interaction != None:
        await ctx_interaction.channel.send(content=content, attachments=attachments)

    else:
        print(content)

        for attachment in attachments:
            print(attachment)

##############################################################
# interaction specifics
class CancelOperationView(discord_ui.View):
    """A cancellation button for long-running operations.

    timeout=None keeps the button active beyond Discord's default 180-second
    view timeout. The view is attached to a normal bot message, not an
    interaction webhook response, so it also works for operations >15 minutes.
    """
    def __init__(self, user_id, cancel_event):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.cancel_event = cancel_event

    @discord_ui.button(
        label="Annuler",
        style=ButtonStyle.danger,
        custom_id="guionbot:cancel_long_operation"
    )
    async def cancel_operation(self, interaction: Interaction, button: discord_ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "Seul l'auteur de la commande peut l'annuler.",
                ephemeral=True
            )
            return

        self.cancel_event.set()
        button.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()


class ConfirmationButtons(discord_ui.View):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.confirmed: bool = False

    @discord_ui.button(label = emojis.check, style = ButtonStyle.blurple)
    async def returnTrue(self, interaction: Interaction, button: discord_ui.Button):
        self.confirmed = True
        await interaction.response.defer()
        self.stop()

    @discord_ui.button(label = emojis.redcross, style = ButtonStyle.blurple)
    async def returnFalse(self, interaction: Interaction, button: discord_ui.Button):
        await interaction.response.defer()
        self.stop()

async def confirmationPrompt(interaction: Interaction, confirmation_prompt: str) -> bool:
    view = ConfirmationButtons()
    await interaction.edit_original_response(content=confirmation_prompt, view=view)
    await view.wait()
    await interaction.edit_original_response(content="En cours...", view=None)
    return view.confirmed


