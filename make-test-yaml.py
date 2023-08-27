import yaml

with open("sloshy.yaml", "r") as src:
    config = yaml.safe_load(src)

for room in config["servers"]["chat.stackoverflow.com"]["rooms"]:
    if "role" in room and room["role"] in ("home", "cc"):
        del room["role"]
    if room["id"] == 233626:
        room["role"] = "home"

with open("room-test.yaml", "w") as dest:
    yaml.safe_dump(config, dest)
