import hashlib
import os
from datetime import datetime, timezone, timedelta
from os.path import join

from git import Repo
from telegram.utils.helpers import escape_markdown
from telethon.sync import TelegramClient
from telethon.tl.custom import Message

os.environ['TZ'] = 'Europe/Moscow'
TZ = timezone(timedelta(hours=3))
TIMESTAMP = datetime.now(TZ)
CHAT_ID = -1001235981203

tree_dir = os.getcwd()

FILENAME = join(tree_dir, f'../lineage-17.1-{TIMESTAMP.strftime("%Y%m%d")}-UNOFFICIAL-platina.zip')
SIGNED_FILENAME = join(tree_dir, f'../lineage-17.1-{TIMESTAMP.strftime("%Y%m%d")}-UNOFFICIAL-platina-signed.zip')

bot = TelegramClient('bot', int(os.environ['API_ID']), os.environ['API_HASH']).start(bot_token=os.environ['TOKEN'])


def update_and_get_tree(s):
    os.chdir(s)
    os.system(f'git fetch --all')
    os.system(f'git reset --hard origin/staging')
    repo = Repo('.')

    commit_msg = escape_markdown(repo.active_branch.commit.message.split("\n")[0])
    res = f'`{repo.active_branch.name}:' \
          f'`{repo.active_branch.commit.hexsha[:7]}\n' \
          f'`{commit_msg}`'
    os.chdir(tree_dir)
    return res


bot.send_message(CHAT_ID, f'⚙️ Build started...\n')
bot.send_message(CHAT_ID, f'⚙️ Syncing main tree...\n')
os.system(f'repo sync')
bot.send_message(CHAT_ID, f'⚙️ Syncing device trees...\n')
bot.send_message(CHAT_ID, f'⚙️ Device tree commit: {update_and_get_tree("device/xiaomi/platina")}\n'
                          f'  Common device tree commit: {update_and_get_tree("device/xiaomi/sdm660-common")}\n'
                          f'  Vendor tree commit: {update_and_get_tree("vendor/xiaomi/platina")}\n'
                          f'  Common vendor tree commit: {update_and_get_tree("vendor/xiaomi/sdm660-common")}\n'
                          f'  Kernel commit: {update_and_get_tree("kernel/xiaomi/platina")}')


def lineage_exec(cmd):
    return os.system('bash -c "source build/envsetup.sh; breakfast platina; ' + cmd.replace('"', '\\"') + '"')


bot.send_message(CHAT_ID, f'⚙️ Building...\n')
if not lineage_exec('mka target-files-package otatools'):
    bot.send_message(CHAT_ID, f'⚙️ Signing...\n')
    lineage_exec(
        './build/tools/releasetools/sign_target_files_apks -o -d '
        '~/.android-certs $OUT/obj/PACKAGING/target_files_intermediates/*-target_files-*.zip signed-target_files.zip;'

        './build/tools/releasetools/ota_from_target_files -k ~/.android-certs/releasekey '
        '--block --backup=true signed-target_files.zip ' + SIGNED_FILENAME)
    build_time = datetime.fromtimestamp(0, tz=TZ) + (datetime.now(TZ) - TIMESTAMP)
    bot.send_message(CHAT_ID, f'✅ Build succeed in a {build_time.strftime("%-M mins %-S secs")}!')
    uploading_msg: Message = bot.send_message(CHAT_ID, '⚙ Uploading, please wait...')
    msg: Message = bot.send_file(CHAT_ID, SIGNED_FILENAME, caption='MD5: `Loading...`', parse_mode='md')
    uploading_msg.delete()
    hash = hashlib.md5()
    with open(SIGNED_FILENAME, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            hash.update(chunk)
    msg.edit(f'MD5: `{hash.hexdigest()}`', parse_mode='md')
else:
    build_time = datetime.fromtimestamp(0, tz=TZ) + (datetime.now(TZ) - TIMESTAMP)
    bot.send_message(CHAT_ID, f'❌ Build failed in a {build_time.strftime("%-M mins %-S secs")}!')