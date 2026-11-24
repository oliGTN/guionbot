# PACKAGE imports
from discord.ext import commands
from discord import File
from discord import app_commands, Interaction
from discord import ui as discord_ui
from discord import ButtonStyle
from io import BytesIO
import asyncio

_cancelable_progress_messages = {}

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

        if await finish_cancelable_progress(interaction, content):
            return
        try:
            await interaction.edit_original_response(content=content)
        except Exception as e:
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

        if not intermediate and await finish_cancelable_progress(
                interaction, content, attachments=attachments):
            return
        try:
            if attachments==[]:
                await interaction.edit_original_response(content=content)
            else:
                await interaction.edit_original_response(content=content, attachments=attachments)
        except Exception as e:
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
# Long-running operations

class CancelOperationView(discord_ui.View):
    """Cancellation control attached to a normal bot-authored channel message.

    timeout=None avoids the default 180-second view timeout. Because progress
    is a regular channel message, edits do not depend on the 15-minute
    interaction webhook token.
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


async def start_cancelable_progress(ctx_interaction, content, initial_message=None,
                                    acknowledgement=None, update_interaction_response=True):
    """Create a normal channel progress message and preserve a clean command acknowledgement."""
    cancel_event = asyncio.Event()
    user = getattr(ctx_interaction, "user", None) or getattr(ctx_interaction, "author", None)
    if user is None:
        raise ValueError("Unable to identify the user who started the operation")

    view = CancelOperationView(user.id, cancel_event)
    message = await ctx_interaction.channel.send(content=content, view=view)

    if acknowledgement is None:
        acknowledgement = "✅ Préparation terminée. Suivi de l'opération dans le message ci-dessous."
    if type(ctx_interaction) == Interaction:
        _cancelable_progress_messages[ctx_interaction.id] = message
        if update_interaction_response:
            try:
                await ctx_interaction.edit_original_response(content=acknowledgement)
            except Exception as e:
                golog.log("WAR", "Unable to acknowledge long-operation preparation: " + repr(e))
    elif initial_message is not None:
        try:
            await initial_message.edit(content=acknowledgement)
        except Exception as e:
            golog.log("WAR", "Unable to update initial command response: " + repr(e))

    return cancel_event, view, message


async def update_cancelable_progress(message, content, view):
    """Edit a persistent progress message while keeping its cancel button."""
    return await message.edit(content=content, view=view)


async def stop_cancelable_progress(
        view, message, final_content="⚠️ Opération arrêtée", delete_message=False):
    """Disable cancellation and leave a finalizable progress message in the channel."""
    if view is not None:
        view.stop()
        for child in view.children:
            child.disabled = True

    if message is None:
        return

    if not delete_message:
        try:
            await message.edit(content=final_content, view=None)
        except Exception as e:
            golog.log("WAR", "Unable to finalize progress message: " + repr(e))
        return

    try:
        await message.delete()
    except Exception as e:
        golog.log("WAR", "Unable to delete progress message: " + repr(e))
        try:
            await message.edit(content=final_content, view=None)
        except Exception as edit_error:
            golog.log("WAR", "Unable to finalize progress message: " + repr(edit_error))


async def finish_cancelable_progress(interaction, content, attachments=None, view=None):
    """Replace progress with the final result, without using the slash webhook."""
    message = _cancelable_progress_messages.pop(interaction.id, None)
    if message is None:
        return False

    try:
        kwargs = {"content": content, "view": view}
        if attachments:
            kwargs["attachments"] = attachments
        await message.edit(**kwargs)
    except Exception as e:
        golog.log("WAR", "Unable to publish final progress result: " + repr(e))
        send_kwargs = {"content": content}
        if attachments:
            send_kwargs["files"] = attachments
        await interaction.channel.send(**send_kwargs)
    return True


def clear_cancelable_progress(interaction):
    if type(interaction) == Interaction:
        _cancelable_progress_messages.pop(interaction.id, None)



##############################################################
# interaction specifics
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


