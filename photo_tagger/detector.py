from PIL import Image, ImageDraw
import torch

_clip_model = None
_clip_processor = None

def _get_clip():
    global _clip_model, _clip_processor
    if _clip_model is None:
        from transformers import CLIPProcessor, CLIPModel
        print("Ładowanie CLIP...")
        _clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        _clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
        print("CLIP gotowy.")
    return _clip_model, _clip_processor

CLIP_CANDIDATES = [
    # --- Ludzie – ogólnie ---
    "a person", "people", "a crowd", "a group of people", "a family",
    "a couple", "a duo", "a trio", "a team",

    # --- Mężczyźni ---
    "a man", "a young man", "an old man", "a boy", "a teenage boy",
    "a man with a beard", "a man with glasses", "a bald man",
    "a man in a suit", "a man in casual clothes", "a muscular man",

    # --- Kobiety ---
    "a woman", "a young woman", "an old woman", "a girl", "a teenage girl",
    "a woman with long hair", "a woman with short hair", "a woman with blonde hair",
    "a woman with dark hair", "a woman with curly hair", "a woman with straight hair",
    "a woman with red hair", "a woman with a ponytail", "a woman with braids",
    "a woman in a dress", "a woman in jeans", "a woman smiling",

    # --- Dzieci ---
    "a child", "a baby", "a toddler", "kids playing", "a newborn",

    # --- Cechy wyglądu ---
    "long hair", "short hair", "curly hair", "straight hair", "blonde hair",
    "dark hair", "red hair", "grey hair", "a beard", "a mustache",
    "a tattoo", "freckles", "a hat on a person",

    # --- Emocje / mimika ---
    "a smiling person", "a laughing person", "a crying person",
    "a serious face", "a surprised face", "an angry person",

    # --- Pozycje / aktywność ludzi ---
    "a person sitting", "a person standing", "a person walking",
    "a person running", "a person jumping", "a person lying down",
    "a person reading", "a person talking on the phone",
    "a person working on a laptop", "a person eating", "a person drinking",
    "a person taking a photo", "a person looking at the camera",
    "a person hugging", "a person shaking hands", "a person dancing",

    # --- Selfie / portret ---
    "a selfie", "a portrait", "a close-up of a face", "an eye",
    "a smile", "lips", "a hand", "fingers", "a face",

    # --- Zwierzęta domowe ---
    "a dog", "a cat", "a rabbit", "a hamster", "a parrot", "a fish",
    "a turtle", "a guinea pig",

    # --- Zwierzęta dzikie ---
    "a bird", "a horse", "a cow", "a sheep", "a pig", "a duck", "a chicken",
    "a lion", "a tiger", "an elephant", "a monkey", "a bear", "a fox",
    "a deer", "a wolf", "a penguin", "a snake", "a spider", "a frog",
    "a whale", "a dolphin", "a shark", "a crocodile", "a giraffe", "a zebra",

    # --- Dom – pomieszczenia ---
    "a bedroom", "a living room", "a kitchen", "a bathroom", "a dining room",
    "a hallway", "a garage", "a basement", "a balcony", "a terrace",

    # --- Dom – elementy ---
    "a wall", "a floor", "a ceiling", "a window", "a door", "a staircase",
    "a carpet", "a rug", "a sofa", "a couch", "a chair", "an armchair",
    "a table", "a desk", "a bed", "a wardrobe", "a shelf", "a bookshelf",
    "a lamp", "a mirror", "a curtain", "a pillow", "a blanket", "a fireplace",
    "a TV", "a monitor", "a screen", "a painting on a wall", "a plant indoors",

    # --- Kuchnia / naczynia ---
    "a mug", "a cup", "a glass", "a bottle", "a plate", "a bowl",
    "a fork", "a knife", "a spoon", "a pan", "a pot", "a kettle",
    "a toaster", "a fridge", "a microwave", "an oven", "a sink",
    "a cutting board", "a blender", "a coffee machine",

    # --- Jedzenie i napoje ---
    "food", "a meal", "a pizza", "a burger", "a sandwich", "a salad",
    "a cake", "bread", "fruit", "vegetables", "coffee", "tea", "a smoothie",
    "sushi", "pasta", "a steak", "fries", "a dessert", "chocolate", "ice cream",
    "an apple", "a banana", "an orange", "grapes", "a strawberry", "a tomato",
    "a lemon", "a watermelon", "a pineapple", "avocado", "a carrot",
    "a beer", "wine", "a cocktail", "juice",

    # --- Elektronika ---
    "a phone", "a smartphone", "a laptop", "a computer", "a keyboard",
    "a mouse", "a camera", "a tablet", "headphones", "earbuds", "a speaker",
    "a printer", "a charger", "a cable", "a remote control", "a smartwatch",
    "a game console", "a joystick", "a drone",

    # --- Biuro / szkoła ---
    "a book", "a magazine", "a newspaper", "a notebook", "a pen", "a pencil",
    "a marker", "scissors", "a ruler", "a calculator", "a globe",
    "a whiteboard", "a blackboard", "a desk with papers",

    # --- Klucze / portfel / codzienne przedmioty ---
    "keys", "a wallet", "a purse", "a bag", "a backpack", "a suitcase",
    "glasses", "sunglasses", "a watch", "a clock", "an umbrella",
    "a lighter", "a cigarette", "a candle", "a flashlight",

    # --- Ubrania i akcesoria ---
    "a shirt", "a t-shirt", "a jacket", "a coat", "a hoodie", "a dress",
    "jeans", "trousers", "shorts", "shoes", "sneakers", "boots", "sandals",
    "a hat", "a cap", "a scarf", "gloves", "a tie", "a suit", "a uniform",
    "jewelry", "a necklace", "a ring", "earrings",

    # --- Transport – pojazdy ---
    "a car", "a sports car", "a bus", "a truck", "a van", "a bicycle",
    "a motorcycle", "a scooter", "a tram", "a train", "a subway",
    "an airplane", "a helicopter", "a rocket", "a boat", "a ship", "a yacht",
    "a taxi", "an ambulance", "a police car", "a fire truck",

    # --- Transport – infrastruktura ---
    "a highway", "a road", "a parking lot", "a garage", "a gas station",
    "a traffic light", "a crosswalk", "a tunnel", "a railway",

    # --- Architektura ---
    "a building", "a skyscraper", "a palace", "a castle", "a church",
    "a cathedral", "a mosque", "a temple", "a synagogue",
    "a house", "a villa", "an apartment block", "a cottage",
    "a bridge", "a tower", "a lighthouse", "a windmill", "a monument",
    "a statue", "a fountain", "a gate", "a fence", "a wall outside",

    # --- Miasto / infrastruktura ---
    "a street", "a sidewalk", "a city", "a town square", "a village",
    "a market", "a shop", "a mall", "a restaurant", "a cafe", "a bar",
    "a hotel", "a school", "a university", "a hospital", "an office building",
    "a factory", "a stadium", "an airport", "a train station",
    "a port", "a harbor", "a construction site",

    # --- Natura – tereny ---
    "a forest", "a jungle", "a mountain", "a volcano", "a hill", "a cliff",
    "a beach", "a coast", "a lake", "a river", "a waterfall", "a swamp",
    "a desert", "a field", "a meadow", "a farm", "a vineyard", "a valley",

    # --- Natura – rośliny ---
    "grass", "trees", "a tree", "flowers", "a rose", "a sunflower",
    "a mushroom", "a cactus", "moss", "leaves", "a bush", "wheat",

    # --- Natura – zjawiska / warunki ---
    "a sunset", "a sunrise", "a sky", "clouds", "stars", "the moon", "the sun",
    "snow", "rain", "fog", "mist", "lightning", "a rainbow", "a storm",
    "a rock", "sand", "ice", "a glacier",

    # --- Sport i aktywność ---
    "football", "basketball", "tennis", "volleyball", "baseball",
    "swimming", "running", "cycling", "skiing", "snowboarding",
    "surfing", "climbing", "yoga", "gym workout", "boxing", "martial arts",
    "fishing", "hunting", "camping", "hiking",

    # --- Rozrywka / kultura ---
    "a concert", "a party", "a wedding", "a birthday party", "a festival",
    "a movie theater", "a theater stage", "a museum exhibit",
    "a carnival", "fireworks", "a parade",

    # --- Sztuka i muzyka ---
    "art", "a painting", "a drawing", "a sketch", "a sculpture", "graffiti",
    "a mural", "a guitar", "a piano", "a violin", "a drum kit",
    "sheet music", "a microphone", "headphones",

    # --- Zabawki / gry ---
    "a toy", "a teddy bear", "building blocks", "a board game",
    "playing cards", "chess", "a puzzle", "a video game",
    "a bicycle for kids", "a swing", "a playground",

    # --- Dokumenty / pieniądze ---
    "a flag", "a sign", "a poster", "a map", "money", "coins",
    "a passport", "an ID card", "a certificate", "a letter",

    # --- Ogólne sceny i konteksty ---
    "an indoor scene", "an outdoor scene", "nature scenery", "urban scenery",
    "a messy room", "a clean room", "a cozy room",
    "daytime", "nighttime", "golden hour", "a crowded place", "an empty place",
    "underwater", "aerial view", "a close-up", "a wide landscape",
]


def detect_objects(image_path, threshold=0.10, top_k=8):
    """
    Wykrywa obiekty/sceny na zdjęciu przy użyciu CLIP.
    Zwraca: (tags, image)
    """
    clip_model, clip_processor = _get_clip()
    image = Image.open(image_path).convert("RGB")

    inputs = clip_processor(
        text=CLIP_CANDIDATES,
        images=image,
        return_tensors="pt",
        padding=True
    )
    with torch.no_grad():
        probs = clip_model(**inputs).logits_per_image.softmax(dim=1)[0]

    results = []
    for i, prob in enumerate(probs):
        score = float(prob)
        if score >= threshold:
            label = CLIP_CANDIDATES[i]
            for prefix in ("a ", "an ", "the "):
                if label.startswith(prefix):
                    label = label[len(prefix):]
                    break
            results.append({"tag": label, "confidence": score})

    results.sort(key=lambda x: x["confidence"], reverse=True)
    tags = results[:top_k]

    return tags, image
