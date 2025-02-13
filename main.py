import asyncio
import time
from typing import Optional
import json
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from universalis import Universalis

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


def get_n_cheapest_worlds(listings, n=10):
    listings = listings.get("listings", [])
    sorted_listings = sorted(listings, key=lambda x: x["pricePerUnit"])

    cheapest_worlds = []
    seen_worlds = set()

    for listing in sorted_listings:
        world = listing["worldName"]
        price = listing["pricePerUnit"]

        if world not in seen_worlds:
            cheapest_worlds.append((world, price))
            seen_worlds.add(world)

        if len(cheapest_worlds) >= n:
            break

    return cheapest_worlds


def lookup_item_id(item_name: str, items: dict) -> Optional[str]:
    """Search for the item id that matches the given English item name."""
    for item_id, names in items.items():
        if names.get("en", "").lower() == item_name.lower():
            return item_id
    return None


@app.get("/api/items")
async def search_items(request: Request, query: str = ""):
    print(query)
    # Get items from Universalis (assuming it's already loaded)
    try:
        items = request.app.state.items
    except AttributeError:
        async with Universalis() as universalis:
            items = universalis.items
            request.app.state.items = items
    print("got it")
    # return 20 matches as {id: name}, query is a string like "fire"
    matches = {}

    for item_id, names in items.items():
        if query.lower() in names.get("en", "").lower():
            matches[item_id] = names["en"]
            if len(matches) >= 20:
                break
    return matches


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    async with Universalis() as universalis:
        worlds = await universalis.worlds()
        # print(json.dumps(worlds))
        data_centers = await universalis.data_centers()

        # Store items in app state for later access
        request.app.state.universalis = universalis
        request.app.state.items = universalis.items
    print(data_centers)  # Debug print to verify content
    # Ensure no None/undefined
    worlds = [world for world in worlds if world is not None]
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "data_centers": data_centers,
            # "worlds_all": worlds,
            "worlds": worlds,
            "results": None,
            "selected_dc": None,
            "selected_home": None,
        },
    )


@app.post("/search", response_class=HTMLResponse)
async def search(
    request: Request,
    item_name: str = Form(...),
    data_center: str = Form(...),
    home_world: int = Form(...),
):
    # Fetch the latest worlds, data centers, and items
    async with Universalis() as universalis:
        worlds = await universalis.worlds()
        data_centers = await universalis.data_centers()
        items = universalis.items

    # Look up the item id using the provided name
    item_id = lookup_item_id(item_name, items)
    if item_id is None:
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "item_names": [names["en"] for names in items.values()],
                "data_centers": data_centers,
                # "worlds_all": worlds,
                "worlds": worlds,
                "results": f"Item '{item_name}' not found.",
                "selected_dc": data_center,
                "selected_home": home_world,
            },
        )

    # Query Universalis for the current data using the given data center and item id.
    async with Universalis() as universalis:
        try:
            current_data = await universalis.current_data(data_center, [item_id])
        except Exception as e:
            return templates.TemplateResponse(
                "index.html",
                {
                    "request": request,
                    "item_names": [names["en"] for names in items.values()],
                    "data_centers": data_centers,
                    # "worlds_all": worlds,
                    "worlds": worlds,
                    "results": f"Error querying Universalis: {e}",
                    "selected_dc": data_center,
                    "selected_home": home_world,
                },
            )

    cheapest_worlds = get_n_cheapest_worlds(current_data)

    # Highlight the user's home world in the results.
    highlighted = []
    for world, price in cheapest_worlds:
        is_home = any(int(home_world) == w["id"] and w["name"] == world for w in worlds)
        highlighted.append((world, "{:,}".format(price), is_home))

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "item_names": [names["en"] for names in items.values()],
            "data_centers": data_centers,
            # "worlds_all": worlds,
            "worlds": worlds,
            "results": highlighted,
            "searched_item": item_name,
            "selected_dc": data_center,
            "selected_home": home_world,
        },
    )


# To run the app, use:
#   uvicorn main:app --reload
