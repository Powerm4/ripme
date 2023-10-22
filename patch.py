import json
import subprocess
from hashlib import sha256

# This script will:
# - read current version
# - increment patch version
# - update version in a few places
# - insert new line in ripme.json with message
# - build ripme
# - add the hash of the latest binary to ripme.json
# - commit all changes
message = input('message: ')

# Strip any spaces that might've been entered before the message
message.lstrip()


def get_ripme_json():
    with open('ripme.json') as dataFile:
        ripmeJson = json.load(dataFile)
    return ripmeJson


def update_hash(current_hash):
    ripmeJson = get_ripme_json()
    with open('ripme.json', 'w') as dataFile:
        ripmeJson["currentHash"] = current_hash
        print(ripmeJson["currentHash"])
        json.dump(ripmeJson, dataFile, indent=4)


def update_change_list(message):
    ripmeJson = get_ripme_json()
    with open('ripme.json', 'w') as dataFile:
        ripmeJson["changeList"].insert(0, message)
        json.dump(ripmeJson, dataFile, indent=4)


currentVersion = get_ripme_json()["latestVersion"]

print(f'Current version {currentVersion}')

versionFields = currentVersion.split('.')
patchCur = int(versionFields[2])
patchNext = patchCur + 1
majorMinor = versionFields[:2]
majorMinor.append(str(patchNext))
nextVersion = '.'.join(majorMinor)

print(f'Updating to {nextVersion}')

substrExpr = f's/{currentVersion}/{nextVersion}/'
subprocess.call(['sed', '-i', '-e', substrExpr, 'src/main/java/com/rarchives/ripme/ui/UpdateUtils.java'])
subprocess.call(
    [
        'git',
        'grep',
        f'DEFAULT_VERSION.*{nextVersion}',
        'src/main/java/com/rarchives/ripme/ui/UpdateUtils.java',
    ]
)

substrExpr = 's/\\\"latestVersion\\\": \\\"' + currentVersion + '\\\"/\\\"latestVersion\\\": \\\"' + \
             nextVersion + '\\\"/'
subprocess.call(['sed', '-i', '-e', substrExpr, 'ripme.json'])
subprocess.call(['git', 'grep', 'latestVersion', 'ripme.json'])

substrExpr = f's/<version>{currentVersion}/<version>{nextVersion}/'
subprocess.call(['sed', '-i', '-e', substrExpr, 'pom.xml'])
subprocess.call(
    ['git', 'grep', f'<version>{nextVersion}</version>', 'pom.xml']
)

commitMessage = f'{nextVersion}: {message}'

update_change_list(commitMessage)


print("Building ripme")
subprocess.call(["mvn", "clean", "compile", "assembly:single"])
print("Stripping jar")
subprocess.call(["mvn", "io.github.zlika:reproducible-build-maven-plugin:0.6:strip-jar"])
print("Hashing .jar file")
openedFile = open(
    f"./target/ripme-{nextVersion}-jar-with-dependencies.jar", "rb"
)
readFile = openedFile.read()
file_hash = sha256(readFile).hexdigest()
print(f"Hash is: {file_hash}")
print("Updating hash")
update_hash(file_hash)
subprocess.call(['git', 'add', '-u'])
subprocess.call(['git', 'commit', '-m', commitMessage])
subprocess.call(['git', 'tag', nextVersion])
print("Remember to run `git push origin master` before release.py")
