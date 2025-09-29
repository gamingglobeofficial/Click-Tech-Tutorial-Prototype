import tkinter as tk
import random, json, os
import math
from random import uniform

# ---------- Config ----------
WIDTH, HEIGHT = 600, 500
CLOUD_COUNT = 8
BG_COLOR = "skyblue"
ACCENT = "red" # Used for accents, now for the clicker button trapezoid
HIGHSCORE_FILE = "highscores.json"
SNAKE_GRID_SIZE = 20 # For Snake game

root = tk.Tk()
root.title("Click Tech Tutorial Prototype")
canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT, bg=BG_COLOR)
canvas.pack()

# ---------- Global state ----------
state = "menu"
ui_buttons, after_ids = [], []
score, score_text_id = 0, None
menu_items = [] # Stores {text, command, button_id} for menu navigation
menu_selection = 0 # Index of the currently selected menu item

# Cloud movement data (holds ID, angle, and radius for rotation)
cloud_data = []
cloud_ids = []

# load/save highscores
def load_highscores():
    if os.path.exists(HIGHSCORE_FILE):
        try:
            with open(HIGHSCORE_FILE, "r") as f:
                return json.load(f)
        except:
            # If loading fails, return an empty dictionary
            return {}
    return {}

def save_highscores_file():
    try:
        with open(HIGHSCORE_FILE, "w") as f:
            json.dump(high_scores, f)
    except:
        # Fail silently if saving fails
        pass

# Ensure all game keys are present in the default structure
high_scores = {"earthprotector":0,"flight":0,"clicker":0,"breakout":0,"snake":0,"drawing":0,"animation":0}
high_scores.update(load_highscores())

# game globals
asteroids, bullets, ship_id = [], [], None
enemies, enemy_bullets, pbot_bullets = [], [], []
pbots = []
buildings, plane_id, flight_speed, hud_text = [], None, 6, None
paddle_id, ball_pairs, brick_ids = None, [], [] # ball_pairs: [{id, dx, dy}]
click_count, clickbtn_id = 0, None
snake_cells, snake_dir, food_pos = [], (1,0), None
is_game_over = False # Generic game over flag

# New global state variables for game updates
clicker_timer = 0 	 	# Timer for Click Clicker
is_cockpit_view = False # State for Flight Simulator
cockpit_ids = [] 	 	# Elements for cockpit view
is_first_start = True 	# Flag for the welcome message
last_x, last_y = 0, 0   # For Drawing Studio

# Drawing Studio State
draw_color = "black"
draw_size = 5

# Animation Studio State
frames = [] # List of canvas item configurations
current_frame_index = 0
animation_running = False
frame_index_text_id = None # Canvas text ID for frame display
drag_data = {"x": 0, "y": 0, "item": None} # For animation shape dragging


# ---------- Utility ----------
def clear_game_tags():
    global score, score_text_id, ui_buttons, menu_items, menu_selection, is_game_over
    is_game_over = False # Reset game over flag
    for aid in after_ids:
        try: root.after_cancel(aid)
        except: pass
    after_ids.clear()
    for item in canvas.find_all():
        # Clouds are persistent, but other items should be cleared
        if "cloud" not in canvas.gettags(item): canvas.delete(item)
    score, score_text_id = 0, None
    reset_game_vars()
    destroy_menu_buttons() # Ensure all UI buttons (including in-game menu button) are destroyed
    menu_items = []
    menu_selection = 0
    # Unbind menu controls
    root.unbind("<Up>"); root.unbind("<Down>"); root.unbind("<Return>")
    # Unbind common game controls
    root.unbind("<Left>"); root.unbind("<Right>"); root.unbind("<space>"); root.unbind("<c>")
    root.unbind("<Button-1>"); root.unbind("<B1-Motion>"); root.unbind("<ButtonRelease-1>")
    root.unbind("<w>"); root.unbind("<a>"); root.unbind("<s>"); root.unbind("<d>")


def reset_game_vars():
    global asteroids, bullets, ship_id, buildings, plane_id
    global paddle_id, ball_pairs, brick_ids, clickbtn_id
    global snake_cells, food_pos, snake_dir, click_count
    global flight_speed, hud_text, enemies, enemy_bullets, pbot_bullets
    global clicker_timer, is_cockpit_view, cockpit_ids, pbots
    global draw_color, draw_size, frames, current_frame_index, animation_running
    
    asteroids, bullets, buildings, ball_pairs, brick_ids = [], [], [], [], []
    enemies, enemy_bullets, pbot_bullets = [], [], []
    pbots = []
    ship_id = plane_id = paddle_id = clickbtn_id = None
    snake_cells, food_pos, snake_dir = [], None, (1,0)
    click_count, flight_speed, hud_text = 0, 6, None
    
    clicker_timer = 0
    is_cockpit_view = False
    cockpit_ids = []

    # Reset Drawing/Animation
    draw_color = "black"
    draw_size = 5
    frames = []
    current_frame_index = 0
    animation_running = False


def to_menu(event=None):
    global state
    state = "menu"
    clear_game_tags()
    _display_main_menu() # Always go to main menu after initial welcome

def destroy_menu_buttons():
    global ui_buttons
    for b in ui_buttons:
        try: b.destroy()
        except: pass
    ui_buttons = []

# ---------- Clouds (Horizontal Drift) ----------
def spawn_clouds():
    global cloud_ids, cloud_data
    
    for c in cloud_ids: canvas.delete(c)
    cloud_ids.clear()
    cloud_data.clear()
    
    for i in range(CLOUD_COUNT):
        x = random.uniform(0, WIDTH)
        y = random.uniform(50, HEIGHT - 100)
        
        w, h = random.randint(50, 100), random.randint(15, 35)
        # Create cloud with a slight gray bottom for depth
        cid = canvas.create_oval(x-w/2, y-h/2, x+w/2, y+h/2, fill="white", outline="", tags=("cloud",))
        canvas.create_oval(x-w/2, y+h/4, x+w/2, y+h/2 + 5, fill="#e0e0e0", outline="", tags=("cloud",))
        
        cloud_ids.append(cid)
        canvas.tag_lower(cid)
        
        cloud_data.append({
            'id': cid,
            'speed': random.uniform(-0.5, -2.5),
            'w': w, 'h': h
        })

def animate_clouds_loop():
    global cloud_data
    
    for data in list(cloud_data):
        try:
            cloud_id = data['id']
            # Move all canvas items associated with this cloud_id tag
            items_to_move = canvas.find_withtag(cloud_id)
            if not items_to_move:
                cloud_data.remove(data)
                continue

            # Move all parts of the cloud
            canvas.move(cloud_id, data['speed'], 0)
            
            bbox = canvas.bbox(cloud_id)
            if not bbox:
                cloud_data.remove(data)
                continue
            
            if bbox[2] < 0:
                reset_x = WIDTH + 10
                dx_reset = reset_x - bbox[0]
                new_y = random.uniform(50, HEIGHT - 100)
                dy_reset = new_y - bbox[1]

                # Move all items with the same tag ("cloud") associated with this ID
                canvas.move(cloud_id, dx_reset, dy_reset)
                
        except tk.TclError:
            if data in cloud_data:
                cloud_data.remove(data)

    aid = root.after(50, animate_clouds_loop)
    after_ids.append(aid)

# ---------- Score & Menu Button (Top Right) ----------
def init_score():
    global score, score_text_id, ui_buttons
    score = 0
    # 1. Place score on the right side
    score_text_id = canvas.create_text(WIDTH - 10, 20, text="Score: 0", font=("Arial", 12, "bold"), fill="black", tags=("score",), anchor="e")
    
    # 2. Add a persistent Menu button that triggers save_highscore() on click
    b = tk.Button(root, text="Menu", command=lambda: (save_highscore(state), to_menu()), bg="lightgray", fg="black", font=("Arial", 10))
    canvas.create_window(WIDTH - 40, 45, window=b, tags=("in_game_button",))
    ui_buttons.append(b)

def add_score(points=1):
    global score
    score += points
    if score_text_id:
        if state == "clicker":
            # Repositioning Click Clicker score text to the left side
            canvas.itemconfigure(score_text_id, text=f"Score: {score} | Time: {clicker_timer}s", anchor="w")
        else:
            canvas.itemconfigure(score_text_id, text=f"Score: {score}", anchor="e")

def save_highscore(game):
    global high_scores, score
    if score > high_scores.get(game,0):
        high_scores[game] = score; save_highscores_file()

# ---------- Menu Navigation and Display ----------

def _display_main_menu():
    global state, ui_buttons, menu_items, menu_selection
    state = "menu"
    canvas.delete("welcome_text"); canvas.delete("menu_text")
    canvas.config(bg=BG_COLOR)
    spawn_clouds()
    
    canvas.create_text(WIDTH//2,40,text="Click Tech Tutorial Prototype",font=("Arial",20,"bold"),fill=ACCENT,tags=("menu_text",))
    
    y=70
    display_scores = high_scores.copy()
    
    # Display high scores and map keys to readable names
    game_map = {
        "earthprotector": "Earth Protector",
        "flight": "Flight Simulator",
        "clicker": "Click Clicker",
        "breakout": "Breakout",
        "snake": "Snake",
        "drawing": "Drawing Studio",
        "animation": "Animation Studio",
    }
    
    # Order the display
    display_order = ["earthprotector", "flight", "clicker", "breakout", "snake", "drawing", "animation"]
    
    for key in display_order:
        if key in display_scores:
            display_name = game_map.get(key, key.title())
            canvas.create_text(WIDTH//2,y,text=f"{display_name} High Score: {display_scores[key]}",font=("Arial",11),fill="black",tags=("menu_text",))
            y+=18

    # Menu items setup
    items=[("Earth Protector",start_asteroid),
           ("Flight Simulator",start_flight),
           ("Click Clicker",show_clicker_time_select),
           ("Breakout",start_breakout),
           ("Snake",start_snake),
           ("Drawing Studio",start_drawing),
           ("Animation Studio",start_animation_studio),
           ("Reset Highscores",reset_highscores),
           ("Quit",root.quit)]
    
    y=200
    menu_items = []
    menu_selection = 0
    
    for t,c in items:
        # Create a button on the canvas
        # Use relief=flat initially, we will change its background color to highlight
        b=tk.Button(root,text=t,command=lambda cc=c:menu_button_pressed(cc),bg="white",fg="black",font=("Arial",11), relief=tk.FLAT)
        ui_buttons.append(b)
        window_id = canvas.create_window(WIDTH//2,y,window=b, tags=("menu_button",))
        
        # Store item data
        menu_items.append({'text': t, 'command': c, 'button': b, 'window_id': window_id})
        y+=40
    
    # Initialize selection highlight
    update_menu_selection()

    # Bind menu controls
    root.bind("<Up>", navigate_menu)
    root.bind("<Down>", navigate_menu)
    root.bind("<Return>", select_menu_item)
    root.bind("<Escape>",lambda e:None)
    animate_clouds_loop()


def navigate_menu(event):
    global menu_selection
    if state != "menu" or not menu_items: return
    
    if event.keysym == "Up":
        menu_selection = (menu_selection - 1) % len(menu_items)
    elif event.keysym == "Down":
        menu_selection = (menu_selection + 1) % len(menu_items)
    
    update_menu_selection()

def update_menu_selection():
    global menu_items, menu_selection
    for i, item in enumerate(menu_items):
        if i == menu_selection:
            # Highlight the selected button in RED
            item['button'].config(bg="red", fg="red", relief=tk.RAISED)
        else:
            # Unhighlight others (back to white)
            item['button'].config(bg= ACCENT, fg="black", relief=tk.FLAT)

def select_menu_item(event):
    if state != "menu" or not menu_items: return
    # Trigger the command of the selected item
    selected_item = menu_items[menu_selection]
    menu_button_pressed(selected_item['command'])

def menu_button_pressed(cmd):
    # Unbind controls before starting game
    root.unbind("<Up>"); root.unbind("<Down>"); root.unbind("<Return>")
    destroy_menu_buttons()
    canvas.delete("menu_text")
    cmd()

def show_welcome_screen():
    global state
    state = "welcome"
    canvas.config(bg=BG_COLOR)
    spawn_clouds()
    
    canvas.create_text(WIDTH//2, HEIGHT//2 - 50,
                        text="Welcome to GamingGlobe Click: Click Tech Tutorial!",
                        font=("Arial", 24, "bold"),
                        fill="darkblue",
                        tags=("welcome_text",))
    
    canvas.create_text(WIDTH//2, HEIGHT//2 + 10,
                        text="This Game features various Technology abilities of the Console!",
                        font=("Arial", 14),
                        fill="black",
                        tags=("welcome_text",))
                        
    aid = root.after(3000, _display_main_menu)
    after_ids.append(aid)

def show_menu(event=None):
    global state, is_first_start
    clear_game_tags()
    
    if is_first_start:
        is_first_start = False
        show_welcome_screen()
    else:
        _display_main_menu()

def reset_highscores():
    global high_scores
    high_scores={k:0 for k in high_scores}; save_highscores_file(); show_menu()

# ---------- Helpers ----------
def collide_by_id(a_id,b_id):
    try:
        a,b=canvas.bbox(a_id),canvas.bbox(b_id)
        if not a or not b: return False
        return a[0]<b[2] and a[2]>b[0] and a[1]<b[3] and a[3]>b[1]
    except: return False

def move_safe(item,dx,dy):
    if item and (isinstance(item, int) and canvas.type(item)) or isinstance(item, str):
        canvas.move(item,dx,dy)

def spawn_particles(x,y,color="orange"):
    for _ in range(6):
        dx,dy=random.randint(-3,3),random.randint(-3,3)
        p=canvas.create_oval(x,y,x+4,y+4,fill=color,outline="")
        animate_particle(p,dx,dy,8)

def large_explosion(x, y):
    for _ in range(40):
        size = random.randint(5, 12)
        dx = uniform(-10, 10)
        dy = uniform(-10, 5)
        color = random.choice(["red", "orange", "yellow"])
        p = canvas.create_oval(x - size/2, y - size/2, x + size/2, y + size/2, fill=color, outline="")
        animate_particle(p, dx, dy, 15)

def animate_particle(p,dx,dy,life):
    if life<=0: canvas.delete(p); return
    canvas.move(p,dx,dy); root.after(50,lambda:animate_particle(p,dx,dy,life-1))

# ---------- Game 1: Earth Protector ----------
def start_asteroid():
    global state,ship_id, pbots
    state="earthprotector"; clear_game_tags(); spawn_clouds()
    
    # Ground Rectangle
    canvas.create_rectangle(0, HEIGHT - 30, WIDTH, HEIGHT, fill="#38761d", outline="", tags=("ground",))
    
    # Player ship
    ship_id=canvas.create_polygon(WIDTH//2,HEIGHT-90,WIDTH//2 - 16,HEIGHT-60,WIDTH//2 + 16,HEIGHT-60,fill=ACCENT, tags=("ship",))
    ship_label_id = canvas.create_text(WIDTH//2, HEIGHT - 100, text="Player Guard", fill="white", font=("Arial", 9, "bold"), tags=("ship_label",))

    # Two AI defense units (P-Bots, all labeled Guard)
    pbot_configs = [
        {"label": "Guard L", "offset": -150, "color": "darkgreen"},
        {"label": "Guard R", "offset": 150, "color": "darkblue"},
    ]

    pbots = []
    for config in pbot_configs:
        x_center = WIDTH // 2 + config["offset"]
        
        p_id = canvas.create_polygon(
            x_center, HEIGHT-90, x_center - 16, HEIGHT-60, x_center + 16, HEIGHT-60,
            fill=config["color"], tags=("pbot",)
        )
        
        label_id = canvas.create_text(x_center, HEIGHT - 100, text=config["label"], fill="white", font=("Arial", 9, "bold"))

        pbots.append({
            'id': p_id,
            'label_id': label_id,
            'dx': 0,
            'label': config['label']
        })
    
    root.bind("<Left>",lambda e:(move_safe(ship_id,-20,0), move_safe(ship_label_id,-20,0)))
    root.bind("<Right>",lambda e:(move_safe(ship_id,20,0), move_safe(ship_label_id,20,0)))
    root.bind("<space>",asteroid_shoot)
    root.bind("<Escape>",lambda e:(save_highscore("earthprotector"),to_menu()))
    
    init_score(); asteroid_spawn_loop(); asteroid_update_loop(); animate_clouds_loop()

def asteroid_shoot(e=None):
    if not ship_id: return
    x1,y1,x2,y2=canvas.bbox(ship_id); bx=(x1+x2)//2
    b=canvas.create_rectangle(bx-2,y1-15,bx+2,y1,fill="yellow"); bullets.append(b)

def asteroid_spawn_loop():
    if state!="earthprotector": return
    
    # Asteroid spawn
    if random.random()<0.15:
        s=random.randint(20,40);x=random.randint(0,WIDTH-s)
        a=canvas.create_oval(x,-s,x+s,0,fill="darkgray"); asteroids.append(a)
        
    # Enemy ship spawn
    if random.random()<0.03:
        w,h=30,15;x=random.randint(50,WIDTH-50)
        e=canvas.create_rectangle(x,-h,x+w,0,fill="blue",tags=("enemy",)); enemies.append(e)

    aid=root.after(300,asteroid_spawn_loop); after_ids.append(aid)

def pbot_move_logic(pbot):
    if not pbot['id']: return

    try:
        pbot_bbox = canvas.bbox(pbot['id'])
        if not pbot_bbox: return
        pbot_cx = (pbot_bbox[0] + pbot_bbox[2]) // 2
    except tk.TclError:
        return

    closest_threat_x = None
    min_dist_y = HEIGHT * 2

    for threat in asteroids + enemies:
        try:
            coords = canvas.coords(threat)
            if not coords: continue
            tx = (coords[0] + coords[2]) // 2
            if coords[3] < pbot_bbox[1]:
                tdist_y = pbot_bbox[1] - coords[3]
                if tdist_y < min_dist_y:
                    min_dist_y = tdist_y
                    closest_threat_x = tx
        except tk.TclError:
            continue

    current_dx = pbot.get('dx', 0)
    
    if closest_threat_x is not None:
        if closest_threat_x < pbot_cx - 20:
            current_dx = -5
        elif closest_threat_x > pbot_cx + 20:
            current_dx = 5
        else:
            current_dx = 0
    
    elif random.random() < 0.05:
        current_dx = random.choice([-5, 0, 5])

    pbot['dx'] = current_dx

    canvas.move(pbot['id'], pbot['dx'], 0)
    canvas.move(pbot['label_id'], pbot['dx'], 0)
    
    pbot_bbox = canvas.bbox(pbot['id'])
    if pbot_bbox:
        if pbot_bbox[0] < 0:
            dx_correct = -pbot_bbox[0]
            canvas.move(pbot['id'], dx_correct, 0)
            canvas.move(pbot['label_id'], dx_correct, 0)
            pbot['dx'] = abs(pbot['dx'])
        elif pbot_bbox[2] > WIDTH:
            dx_correct = WIDTH - pbot_bbox[2]
            canvas.move(pbot['id'], dx_correct, 0)
            canvas.move(pbot['label_id'], dx_correct, 0)
            pbot['dx'] = -abs(pbot['dx'])

def asteroid_update_loop():
    global pbots
    
    if state!="earthprotector": return
    
    # 1. P-Bot Movement Logic
    for pbot in list(pbots):
        pbot_move_logic(pbot)
    
    # 2. Move Asteroids
    for a in list(asteroids):
        asteroid_deleted = False
        
        canvas.move(a,0,9)
        
        def destroy_unit(unit_id, label_tag, game_over_msg):
            large_explosion(*canvas.coords(unit_id)[:2])
            save_highscore("earthprotector")
            canvas.delete(unit_id)
            if label_tag: # Only try to delete label if a tag is provided (for ships/pbots)
                # Delete the label using its ID, which is the first item in the tuple returned by find_withtag
                label_id_tuple = canvas.find_withtag(label_tag)
                if label_id_tuple:
                    canvas.delete(label_id_tuple[0])
            canvas.create_text(WIDTH//2,HEIGHT//2,text=game_over_msg,font=("Arial",20),fill=ACCENT)

        # Ship collision
        ship_label_id = canvas.find_withtag("ship_label")
        if ship_id and collide_by_id(ship_id,a):
            destroy_unit(ship_id, "ship_label", "Ship Destroyed!"); return

        # Pbot collision
        for pbot in list(pbots):
            if collide_by_id(pbot['id'], a):
                spawn_particles(*canvas.coords(pbot['id'])[:2], color="green")
                canvas.delete(a); asteroids.remove(a)
                canvas.delete(pbot['id']); canvas.delete(pbot['label_id'])
                pbots.remove(pbot)
                add_score(50); asteroid_deleted = True; break
            
        if asteroid_deleted: continue

        # Ground collision
        if canvas.coords(a)[3] >= HEIGHT - 30:
            canvas.delete(a); asteroids.remove(a)
            destroy_unit(ship_id, "ship_label", "Earth Destroyed!"); return # Game over if earth is hit
            
    # 3. Move Player/Pbot Bullets and Check Collisions
    for b in list(bullets):
        canvas.move(b,0,-18)
        if canvas.coords(b)[1]<0:
            canvas.delete(b); bullets.remove(b); continue
        
        hit = False
        for target_list in [asteroids, enemies]:
            for target in list(target_list):
                if collide_by_id(target,b):
                    spawn_particles(*canvas.coords(target)[:2], color="orange")
                    canvas.delete(target); target_list.remove(target); add_score(10 if target_list is asteroids else 20)
                    hit = True; break
            if hit: break
        if hit:
            canvas.delete(b); bullets.remove(b); continue
    
    # 4. Friendly AI Shoot (P-Bot)
    for pbot in list(pbots):
        if random.random() < 0.1: # Increased AI shooting rate
            try:
                px1,py1,px2,py2=canvas.bbox(pbot['id']); pbx=(px1+px2)//2
                pb=canvas.create_rectangle(pbx-2,py1-15,pbx+2,py1,fill="lime"); bullets.append(pb)
            except tk.TclError: pass

    # 5. Move Enemies, Shoot, and Check Ship/Pbot Collision
    for e in list(enemies):
        enemy_deleted = False
        canvas.move(e,0,4)
        
        # Enemy shooting logic
        if ship_id and random.random() < 0.005:
            ex1,ey1,ex2,ey2=canvas.bbox(e); ebx=(ex1+ex2)//2; eby=(ey1+ey2)//2
            eb=canvas.create_rectangle(ebx-2,eby,ebx+2,eby+10,fill="magenta"); enemy_bullets.append(eb)

        # Enemy collision with player ship
        ship_label_id = canvas.find_withtag("ship_label")
        if ship_id and collide_by_id(ship_id, e):
            destroy_unit(ship_id, "ship_label", "Ship Destroyed!"); return

        # Enemy collision with P-Bots
        for pbot in list(pbots):
            if collide_by_id(pbot['id'], e):
                spawn_particles(*canvas.coords(pbot['id'])[:2], color="green")
                canvas.delete(e); enemies.remove(e)
                canvas.delete(pbot['id']); canvas.delete(pbot['label_id'])
                pbots.remove(pbot); add_score(50); enemy_deleted = True; break
        
        if enemy_deleted: continue
        if canvas.coords(e)[1]>HEIGHT: canvas.delete(e); enemies.remove(e)

    # 6. Move Enemy Bullets and Check Ship/Pbot Collision
    for eb in list(enemy_bullets):
        canvas.move(eb,0,8)
        if canvas.coords(eb)[3]>HEIGHT:
            canvas.delete(eb); enemy_bullets.remove(eb); continue
        
        # Enemy Bullet vs Ship
        ship_label_id = canvas.find_withtag("ship_label")
        if ship_id and collide_by_id(ship_id, eb):
            canvas.delete(eb); enemy_bullets.remove(eb)
            destroy_unit(ship_id, "ship_label", "Ship Destroyed!"); return
            
        # Enemy Bullet vs Pbot
        for pbot in list(pbots):
            if collide_by_id(pbot['id'], eb):
                canvas.delete(eb); enemy_bullets.remove(eb)
                spawn_particles(*canvas.coords(pbot['id'])[:2], color="green")
                canvas.delete(pbot['id']); canvas.delete(pbot['label_id'])
                pbots.remove(pbot); add_score(50); break

        # Enemy Bullet vs Ground
        if canvas.coords(eb)[3] >= HEIGHT - 30:
            spawn_particles(canvas.coords(eb)[0], HEIGHT - 30, color="gray")
            canvas.delete(eb); enemy_bullets.remove(eb)

    aid=root.after(30,asteroid_update_loop); after_ids.append(aid)

# ---------- Game 2: Flight Simulator (Textured & Cockpit Fix) ----------

def handle_flight_input(dx, dy):
    """Handles plane movement input based on view mode."""
    if state != "flight": return
    global is_cockpit_view
    
    # 1. Always move the invisible plane object for collision/altitude tracking
    move_safe(plane_id, dx, dy)

    if is_cockpit_view:
        # 2. If in cockpit view, move the WORLD objects (buildings, clouds, ground)
        # in the OPPOSITE direction of the control input.
        
        # Move Buildings (building structure is stored as a list of item IDs)
        for b_list in buildings:
            for b_id in b_list:
                canvas.move(b_id, -dx, -dy)
        
        # Move Clouds
        for c_data in cloud_data:
            # Move the associated items (main cloud and shadow) by moving the ID
            try:
                if canvas.type(c_data['id']):
                    canvas.move(c_data['id'], -dx, -dy)
            except tk.TclError:
                pass # Cloud might have been deleted/recreated during loop

        
        # Move Ground
        canvas.move("ground", -dx, -dy)

def start_flight():
    global state,plane_id,hud_text,flight_speed, is_cockpit_view
    state="flight"; clear_game_tags(); canvas.config(bg="lightblue"); spawn_clouds()
    
    # Ground (Textured Green)
    canvas.create_rectangle(0, HEIGHT - 50, WIDTH, HEIGHT, fill="#38761d", outline="#1e4600", tags=("ground",))

    is_cockpit_view = False
    
    # The plane is a simple shape for collision tracking, hidden in cockpit view
    plane_id=canvas.create_polygon(WIDTH//3,HEIGHT//2,WIDTH//3-20,HEIGHT//2-10,WIDTH//3-20,HEIGHT//2+10,fill="gray", tags=("plane",))
    
    # HUD text repositioned to top-left to avoid top-right score/menu
    hud_text=canvas.create_text(10,20,text="Alt: 0 | Spd: 0 | View: External",font=("Arial",12),fill="black",tags=("hud",), anchor="w")
    
    # Bind controls
    root.bind("<Left>",lambda e:handle_flight_input(-12, 0))
    root.bind("<Right>",lambda e:handle_flight_input(12, 0))
    root.bind("<Up>",lambda e:handle_flight_input(0, -12))
    root.bind("<Down>",lambda e:handle_flight_input(0, 12))
    
    root.bind("<c>", toggle_cockpit_view)
    root.bind("<Escape>",lambda e:(save_highscore("flight"),to_menu()))
    
    init_score(); flight_spawn_loop(); flight_update_loop(); animate_clouds_loop()

def toggle_cockpit_view(event=None):
    global is_cockpit_view, plane_id, cockpit_ids, hud_text
    if state != "flight": return
    
    is_cockpit_view = not is_cockpit_view
    
    for cid in cockpit_ids: canvas.delete(cid)
    cockpit_ids.clear()

    if is_cockpit_view:
        canvas.itemconfigure(plane_id, state='hidden')
        
        # Cockpit Frame
        horizon = canvas.create_line(0, HEIGHT - 50, WIDTH, HEIGHT - 50, fill="yellow", width=2, tags=("cockpit",))
        frame_l = canvas.create_rectangle(0, 0, 30, HEIGHT, fill="#2c3e50", outline="", tags=("cockpit",))
        frame_r = canvas.create_rectangle(WIDTH-30, 0, WIDTH, HEIGHT, fill="#2c3e50", outline="", tags=("cockpit",))
        
        # Center display
        center_x = WIDTH // 2
        center_y = HEIGHT * 0.95
        frame_c = canvas.create_polygon(
            center_x - 50, HEIGHT, center_x + 50, HEIGHT,
            center_x + 15, center_y, center_x - 15, center_y,
            fill="#555", outline="#777", tags=("cockpit",)
        )
        
        cockpit_ids.extend([horizon, frame_l, frame_r, frame_c])
        
        # Move HUD to cockpit position (bottom center)
        canvas.coords(hud_text, WIDTH//2, HEIGHT - 20)
        canvas.itemconfigure(hud_text, fill="white", anchor="center")
        
    else:
        canvas.itemconfigure(plane_id, state='normal')
        
        # Move HUD back to external position (top left)
        canvas.coords(hud_text, 10, 20)
        canvas.itemconfigure(hud_text, fill="black", anchor="w")

def flight_spawn_loop():
    if state!="flight": return
    if random.random()<0.25:
        # Textured Building Spawn
        w,h=random.randint(30,50),random.randint(80,160)
        x_start = WIDTH + 10
        y_ground = HEIGHT - 50
        
        # Main Building Body (Greyish/Concrete)
        b_body = canvas.create_rectangle(x_start, y_ground - h, x_start + w, y_ground,
                                     fill="#5e5e5e", outline="#333", width=1)
        # Roof (Maroon/Textured)
        roof_h = h // 8
        b_roof = canvas.create_rectangle(x_start - 2, y_ground - h - roof_h, x_start + w + 2, y_ground - h,
                                     fill="#a64d79", outline="#772b52")
        
        # Store both items together
        buildings.append([b_body, b_roof])
    aid=root.after(700,flight_spawn_loop); after_ids.append(aid)

def flight_update_loop():
    global flight_speed, plane_id
    if state!="flight" or not plane_id: return
    flight_speed=6+score//10
    
    # 1. Constant forward movement of the world
    for b_list in list(buildings):
        # Buildings always move towards the plane at flight_speed
        is_gone = False
        for b_id in b_list:
            canvas.move(b_id,-flight_speed,0)
            try:
                if canvas.coords(b_id)[2]<0:
                    canvas.delete(b_id)
                    is_gone = True
            except tk.TclError: # Handle case where the item might have been deleted already
                is_gone = True
                
        
        if is_gone:
            buildings.remove(b_list)
            add_score(1)
            continue
        
        # Collision Check (only check the main body ID)
        if plane_id and collide_by_id(plane_id, b_list[0]):
            # --- CRASH LOGIC ---
            bbox = canvas.bbox(plane_id)
            if bbox: large_explosion((bbox[0]+bbox[2])/2, (bbox[1]+bbox[3])/2)
            
            save_highscore("flight")
            canvas.create_text(WIDTH//2,HEIGHT//2,text="Crashed",font=("Arial",20),fill=ACCENT)
            canvas.delete(plane_id); plane_id = None; return
            
    # 2. Plane auto-moves forward slowly (moves only the hidden plane object, not the world)
    move_safe(plane_id,flight_speed//4,0)
    
    if plane_id:
        bbox = canvas.bbox(plane_id)
        if not bbox:
            aid=root.after(50,flight_update_loop); after_ids.append(aid); return

        x1,y1,x2,y2 = bbox
        cx,cy=(x1+x2)//2,(y1+y2)//2
        alt=max(0, (HEIGHT - 50) - cy)
        
        view_text = 'Cockpit' if is_cockpit_view else 'External'
        canvas.itemconfigure("hud",text=f"Alt: {alt:.0f} | Spd: {flight_speed} | View: {view_text}")
        
        if y2 >= HEIGHT - 50:
            # --- GROUND CRASH LOGIC ---
            spawn_particles(cx, cy, color="darkgreen")
            save_highscore("flight")
            canvas.create_text(WIDTH//2,HEIGHT//2,text="Crashed on Ground",font=("Arial",20),fill=ACCENT)
            canvas.delete(plane_id); plane_id = None; return
            
    aid=root.after(50,flight_update_loop); after_ids.append(aid)

# ---------- Game 3: Click Clicker (Fixed Polygon Coords) ----------

def show_clicker_time_select():
    global state, ui_buttons
    state = "clicker_select"
    destroy_menu_buttons()
    canvas.delete("menu_text")
    
    canvas.create_text(WIDTH//2, 80, text="Choose Game Time (Seconds)", font=("Arial", 16, "bold"), fill=ACCENT, tags=("menu_text",))

    times = [10, 30, 60]
    y_start = 150
    
    for t in times:
        b = tk.Button(root, text=f"{t} Seconds",
                      command=lambda time=t: start_clicker(time),
                      bg="white", fg="darkgreen", font=("Arial", 11, "bold"))
        ui_buttons.append(b)
        canvas.create_window(WIDTH//2, y_start, window=b)
        y_start += 50
    
    b = tk.Button(root, text="Back to Menu", command=to_menu, bg="lightgray", fg="black", font=("Arial", 10))
    ui_buttons.append(b)
    canvas.create_window(WIDTH//2, y_start + 50, window=b)

def start_clicker(time_limit=30):
    global state, clickbtn_id, click_count, clicker_timer, score_text_id
    state="clicker"; clear_game_tags(); spawn_clouds()
    click_count=0
    clicker_timer = time_limit
    
    btn_w, btn_h_total = 80, 40
    y_center = HEIGHT // 2
    x1, x2 = WIDTH // 2 - btn_w // 2, WIDTH // 2 + btn_w // 2
    rect_y1, rect_y2 = y_center, y_center + 20
    
    rect_id = canvas.create_rectangle(x1, rect_y1, x2, rect_y2, fill="darkgray", tags=("clickbtn",))
    
    trap_y1, trap_y2 = y_center - 20, y_center
    
    # --- FIX: CORRECTED POLYGON COORDINATES (8 coordinates expected) ---
    trap_id = canvas.create_polygon(
        x1, trap_y2,       # Bottom-left (on y_center)
        x2, trap_y2,       # Bottom-right
        x2 - 10, trap_y1,  # Top-right (tapered in 10px)
        x1 + 10, trap_y1,  # Top-left (tapered in 10px)
        fill=ACCENT, outline="darkred", tags=("clickbtn",)
    )
    clickbtn_id = trap_id

    # Bind click event to the button area
    canvas.tag_bind("clickbtn", "<Button-1>", clicker_clicked)
    
    # Delete the score text placed by init_score (if it exists)
    canvas.delete("score")
    
    # Reposition score text to the left side and initialize the timer
    score_text_id = canvas.create_text(10, 20, text=f"Score: 0 | Time: {clicker_timer}s", 
                                       font=("Arial", 12, "bold"), fill="black", tags=("score",), anchor="w")
    init_score() # Re-call to ensure menu button is placed and score_text_id is handled
    
    # Ensure the new score text is on top of the old score text/elements
    canvas.tag_raise(score_text_id) 

    # Start the timer loop
    clicker_timer_loop(time_limit)
    root.bind("<Escape>",lambda e:(save_highscore("clicker"),to_menu()))

def clicker_clicked(event):
    """Handles a mouse click on the button."""
    global click_count
    if state != "clicker" or is_game_over: return
    
    # Check if the button object exists and the event coordinates are within it
    if clickbtn_id and canvas.find_withtag(tk.CURRENT):
        # Only register click if the target is tagged "clickbtn"
        current_tags = canvas.gettags(tk.CURRENT)
        if "clickbtn" in current_tags:
            click_count += 1
            add_score(1)
            # Simple visual feedback: move button slightly down and back up
            canvas.move("clickbtn", 0, 2)
            root.after(50, lambda: canvas.move("clickbtn", 0, -2))
            # Spawn tiny particles for effect
            spawn_particles(event.x, event.y, color="yellow")

def clicker_timer_loop(time_remaining):
    """Counts down the timer and ends the game."""
    global clicker_timer, score_text_id, is_game_over
    if state != "clicker" or is_game_over: return
    
    clicker_timer = time_remaining
    if score_text_id:
        canvas.itemconfigure(score_text_id, text=f"Score: {click_count} | Time: {clicker_timer}s")

    if time_remaining <= 0:
        is_game_over = True
        save_highscore("clicker")
        
        # Display results
        canvas.create_text(WIDTH//2, HEIGHT//2 + 80, 
                           text=f"Time's Up! Final Clicks: {click_count}", 
                           font=("Arial", 20, "bold"), fill="darkgreen")
        
        # Unbind the click event
        canvas.tag_unbind("clickbtn", "<Button-1>")
        return
        
    aid = root.after(1000, lambda: clicker_timer_loop(time_remaining - 1))
    after_ids.append(aid)


# ---------- Game 4: Breakout ----------
def start_breakout():
    global state, paddle_id, ball_pairs, brick_ids
    state = "breakout"; clear_game_tags(); canvas.config(bg="gray20")
    
    # 1. Paddle
    paddle_w, paddle_h = 80, 10
    paddle_id = canvas.create_rectangle(WIDTH // 2 - paddle_w // 2, HEIGHT - 30, 
                                        WIDTH // 2 + paddle_w // 2, HEIGHT - 30 + paddle_h, 
                                        fill="white", tags=("paddle",))
    
    # 2. Ball
    ball_size = 8
    ball_id = canvas.create_oval(WIDTH // 2 - ball_size, HEIGHT // 2 - ball_size, 
                                 WIDTH // 2 + ball_size, HEIGHT // 2 + ball_size, 
                                 fill="yellow", tags=("ball",))
    ball_pairs.append({'id': ball_id, 'dx': random.choice([-5, 5]), 'dy': -5})
    
    # 3. Bricks
    brick_w, brick_h = 50, 20
    rows, cols = 4, WIDTH // brick_w
    colors = ["red", "orange", "yellow", "green"]
    y_start = 50
    brick_ids = []
    
    for r in range(rows):
        color = colors[r % len(colors)]
        for c in range(cols):
            x1 = c * brick_w
            x2 = (c + 1) * brick_w - 2 # -2 for spacing
            y1 = y_start + r * brick_h
            y2 = y_start + (r + 1) * brick_h - 2
            
            if x2 < WIDTH:
                b_id = canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="gray50", tags=("brick",))
                brick_ids.append(b_id)
                
    # 4. Controls
    root.bind("<Left>", lambda e: canvas.move(paddle_id, -20, 0))
    root.bind("<Right>", lambda e: canvas.move(paddle_id, 20, 0))
    root.bind("<Escape>",lambda e:(save_highscore("breakout"),to_menu()))
    
    init_score()
    breakout_update_loop()


def breakout_update_loop():
    global is_game_over
    if state != "breakout" or is_game_over: return
    
    # Check for Win condition
    if not brick_ids and not is_game_over:
        is_game_over = True
        save_highscore("breakout")
        canvas.create_text(WIDTH//2,HEIGHT//2,text="LEVEL CLEARED!",font=("Arial",20,"bold"),fill="lime")
        return

    for ball in list(ball_pairs):
        bid, dx, dy = ball['id'], ball['dx'], ball['dy']
        canvas.move(bid, dx, dy)
        
        # Get ball bounding box
        bbox = canvas.bbox(bid)
        if not bbox: ball_pairs.remove(ball); continue
        x1, y1, x2, y2 = bbox
        
        # Wall Collision
        if x1 <= 0 or x2 >= WIDTH:
            ball['dx'] *= -1
        if y1 <= 0:
            ball['dy'] *= -1
            
        # Paddle Collision
        if paddle_id and collide_by_id(paddle_id, bid) and dy > 0:
            ball['dy'] *= -1
            # Adjust dx based on where it hit the paddle for better control
            paddle_bbox = canvas.bbox(paddle_id)
            ball_center_x = (x1 + x2) / 2
            paddle_center_x = (paddle_bbox[0] + paddle_bbox[2]) / 2
            offset = ball_center_x - paddle_center_x
            # Max deviation of +/- 6
            ball['dx'] = offset / 10 
            
            
        # Brick Collision
        hit_brick = canvas.find_overlapping(x1, y1, x2, y2)
        for item in hit_brick:
            if item in brick_ids:
                brick_ids.remove(item)
                canvas.delete(item)
                
                # Simple flip for now:
                ball['dy'] *= -1
                
                add_score(10)
                spawn_particles((x1+x2)/2, (y1+y2)/2, color="lightgray")
                break
                
        # Floor Collision (Game Over for this ball)
        if y1 >= HEIGHT:
            canvas.delete(bid); ball_pairs.remove(ball)
            if not ball_pairs and not is_game_over:
                # Game over
                is_game_over = True
                save_highscore("breakout")
                canvas.create_text(WIDTH//2,HEIGHT//2,text="GAME OVER",font=("Arial",20),fill=ACCENT)
                return

    aid = root.after(30, breakout_update_loop)
    after_ids.append(aid)

# ---------- Game 5: Snake ----------
def start_snake():
    global state, snake_cells, food_pos, snake_dir, is_game_over
    state = "snake"; clear_game_tags(); canvas.config(bg="gray10")
    is_game_over = False
    
    # Initial setup
    snake_cells = []
    snake_dir = (1, 0) # Start moving right
    
    # Draw Grid (optional, for visibility)
    for i in range(WIDTH // SNAKE_GRID_SIZE):
        canvas.create_line(i * SNAKE_GRID_SIZE, 0, i * SNAKE_GRID_SIZE, HEIGHT, fill="gray30")
    for j in range(HEIGHT // SNAKE_GRID_SIZE):
        canvas.create_line(0, j * SNAKE_GRID_SIZE, WIDTH, j * SNAKE_GRID_SIZE, fill="gray30")
        
    # Initial Snake (start at center)
    start_x = (WIDTH // SNAKE_GRID_SIZE // 2) * SNAKE_GRID_SIZE
    start_y = (HEIGHT // SNAKE_GRID_SIZE // 2) * SNAKE_GRID_SIZE
    
    # Snake body is a list of [x, y] coordinates
    snake_cells.append([start_x, start_y])
    snake_cells.append([start_x - SNAKE_GRID_SIZE, start_y])
    snake_cells.append([start_x - 2 * SNAKE_GRID_SIZE, start_y])
    
    # Draw initial snake (loop only draws the body color)
    for x, y in snake_cells:
        canvas.create_rectangle(x, y, x + SNAKE_GRID_SIZE, y + SNAKE_GRID_SIZE, 
                                fill="green", tags=("snake_body",))
        
    # Draw head color separately
    draw_snake_head(snake_cells[0][0], snake_cells[0][1], is_new=True)
    
    # Spawn food
    spawn_food()
    
    # Controls
    root.bind("<Up>", lambda e: set_snake_dir(0, -1))
    root.bind("<Down>", lambda e: set_snake_dir(0, 1))
    root.bind("<Left>", lambda e: set_snake_dir(-1, 0))
    root.bind("<Right>", lambda e: set_snake_dir(1, 0))
    root.bind("<Escape>",lambda e:(save_highscore("snake"),to_menu()))
    
    init_score()
    snake_update_loop()

def draw_snake_head(x, y, is_new=False):
    """Redraws the head cell with a different color."""
    
    # 1. Change the previous head cell's color to body green (if it exists)
    for item in canvas.find_withtag("snake_head"):
        # The head is now a body segment
        canvas.itemconfigure(item, fill="green")
        canvas.dtag(item, "snake_head")
            
    # 2. Draw/Update the new head
    head_coords = [x, y, x + SNAKE_GRID_SIZE, y + SNAKE_GRID_SIZE]
    
    # Find the item at the new head's coordinates (should be the last segment drawn if new, or the tail being moved)
    overlapping = canvas.find_overlapping(*head_coords)
    found = False
    for item in overlapping:
        tags = canvas.gettags(item)
        if "snake_body" in tags and "food" not in tags:
            # Change existing body segment to head color
            canvas.itemconfigure(item, fill="lime", tags=("snake_body", "snake_head"))
            found = True
            break
            
    if not found:
        # If no overlapping body segment found (e.g., first segment draw)
        canvas.create_rectangle(x, y, x + SNAKE_GRID_SIZE, y + SNAKE_GRID_SIZE,
                                fill="lime", tags=("snake_body", "snake_head"))


def set_snake_dir(dx, dy):
    global snake_dir
    if state != "snake" or is_game_over: return
    # Prevent reversing direction immediately
    if (dx, dy) != (-snake_dir[0], -snake_dir[1]):
        snake_dir = (dx, dy)

def spawn_food():
    global food_pos
    canvas.delete("food")
    
    while True:
        # Calculate max grid positions
        max_x = WIDTH // SNAKE_GRID_SIZE - 1
        max_y = HEIGHT // SNAKE_GRID_SIZE - 1
        
        # Generate random grid coordinates
        fx = random.randint(0, max_x) * SNAKE_GRID_SIZE
        fy = random.randint(0, max_y) * SNAKE_GRID_SIZE
        
        # Check if food is inside snake body
        is_on_snake = any(cell[0] == fx and cell[1] == fy for cell in snake_cells)
        
        if not is_on_snake:
            food_pos = [fx, fy]
            # Draw a shiny red circle/oval for the food
            canvas.create_oval(fx + 2, fy + 2, fx + SNAKE_GRID_SIZE - 2, fy + SNAKE_GRID_SIZE - 2, 
                               fill="red", outline="orange", width=2, tags=("food",))
            break

def snake_game_over():
    global is_game_over
    is_game_over = True
    save_highscore("snake")
    
    canvas.create_text(WIDTH//2,HEIGHT//2,
                       text=f"GAME OVER! Length: {len(snake_cells)}",
                       font=("Arial",20,"bold"),fill=ACCENT)

def snake_update_loop():
    global snake_cells, food_pos, snake_dir
    if state != "snake" or is_game_over: return
    
    # Calculate new head position
    head_x, head_y = snake_cells[0]
    new_head_x = head_x + snake_dir[0] * SNAKE_GRID_SIZE
    new_head_y = head_y + snake_dir[1] * SNAKE_GRID_SIZE
    
    # 1. Collision Checks
    
    # Wall collision
    if (new_head_x < 0 or new_head_x >= WIDTH or 
        new_head_y < 0 or new_head_y >= HEIGHT):
        snake_game_over(); return
        
    # Self collision (check against the body segments, excluding the current head)
    if [new_head_x, new_head_y] in snake_cells[1:]:
        snake_game_over(); return
        
    # 2. Movement and Food
    
    # Add new head to the front
    snake_cells.insert(0, [new_head_x, new_head_y])
    
    # Food check
    if new_head_x == food_pos[0] and new_head_y == food_pos[1]:
        # Don't pop the tail (grow)
        spawn_food()
        add_score(10)
    else:
        # Pop the tail (move normally)
        tail_x, tail_y = snake_cells.pop()
        
        # Delete the canvas object corresponding to the old tail
        tail_coords = [tail_x, tail_y, tail_x + SNAKE_GRID_SIZE, tail_y + SNAKE_GRID_SIZE]
        items_at_tail = canvas.find_overlapping(*tail_coords)
        for item in items_at_tail:
            tags = canvas.gettags(item)
            # Find the body segment that matches the tail coordinates and delete it
            if "snake_body" in tags and "food" not in tags and list(canvas.coords(item)) == tail_coords:
                canvas.delete(item)
                break
        
    # 3. Redraw (update head and body color)
    draw_snake_head(head_x, head_y) # Change old head to body
    draw_snake_head(new_head_x, new_head_y, is_new=True) # Draw new head
    
    aid = root.after(150, snake_update_loop) # Speed
    after_ids.append(aid)

# ---------- Game 6: Drawing Studio ----------
def start_drawing():
    global state, draw_color, draw_size, last_x, last_y
    state = "drawing"; clear_game_tags(); canvas.config(bg="white")
    
    draw_color = "black"
    draw_size = 5
    
    # Draw the control panel for drawing
    control_panel_h = 40
    canvas.create_rectangle(0, HEIGHT - control_panel_h, WIDTH, HEIGHT, 
                            fill="gray80", outline="", tags=("drawing_ui",))
    
    # Color buttons
    colors = ["black", "red", "blue", "green", "yellow", "white"]
    x_offset = 10
    for color in colors:
        b = tk.Button(root, text="", width=2, bg=color, 
                      command=lambda c=color: set_draw_color(c), relief=tk.RAISED)
        ui_buttons.append(b)
        canvas.create_window(x_offset, HEIGHT - 20, window=b)
        x_offset += 30
        
    # Size buttons
    sizes = [3, 6, 10, 20]
    for size in sizes:
        b = tk.Button(root, text=f"{size}", bg="white", fg="black", 
                      command=lambda s=size: set_draw_size(s), font=("Arial", 8))
        ui_buttons.append(b)
        canvas.create_window(x_offset + 10, HEIGHT - 20, window=b)
        x_offset += 40
        
    # Clear Button
    b_clear = tk.Button(root, text="Clear", bg="red", fg="white", 
                        command=clear_drawing_canvas, font=("Arial", 10))
    ui_buttons.append(b_clear)
    canvas.create_window(WIDTH - 50, HEIGHT - 20, window=b_clear)
    
    # Bind drawing events
    canvas.bind("<Button-1>", draw_motion_start)
    canvas.bind("<B1-Motion>", draw_motion)
    canvas.bind("<ButtonRelease-1>", draw_motion_end)
    root.bind("<Escape>",to_menu) # No highscore for drawing

def clear_drawing_canvas():
    """Deletes all items except the control panel."""
    # Find all items except those tagged as drawing_ui
    all_items = set(canvas.find_all())
    ui_items = set(canvas.find_withtag("drawing_ui"))
    
    # Get all items that are NOT part of the UI
    items_to_delete = list(all_items - ui_items)

    for item in items_to_delete:
        canvas.delete(item)

def set_draw_color(color):
    global draw_color
    draw_color = color

def set_draw_size(size):
    global draw_size
    draw_size = size

def draw_motion_start(event):
    global last_x, last_y
    if state != "drawing" or event.y > HEIGHT - 40: return # Ignore clicks on the control panel
    last_x, last_y = event.x, event.y

def draw_motion(event):
    global last_x, last_y
    if state != "drawing" or event.y > HEIGHT - 40: return # Ignore drawing on the control panel
    
    # Draw a line from the last known position to the current position
    canvas.create_line(last_x, last_y, event.x, event.y, 
                       fill=draw_color, width=draw_size, 
                       capstyle=tk.ROUND, smooth=tk.TRUE)
                       
    # Update last position
    last_x, last_y = event.x, event.y

def draw_motion_end(event):
    pass # No specific action needed on release

# ---------- Game 7: Animation Studio (The requested feature) ----------
def start_animation_studio():
    global state, frames, current_frame_index, animation_running, frame_index_text_id
    state = "animation"; clear_game_tags(); canvas.config(bg="lightgray")
    
    frames = [] # List of frame dictionary: {item_id: {type, coords, fill, ...}}
    current_frame_index = 0
    animation_running = False
    
    # Create control panel at the bottom
    control_panel_h = 60
    canvas.create_rectangle(0, HEIGHT - control_panel_h, WIDTH, HEIGHT, 
                            fill="gray80", outline="", tags=("anim_ui_bg",))
    
    # Frame Navigation/Control Buttons
    btn_y = HEIGHT - 30
    x_offset = 10
    
    # Record Frame
    b_record = tk.Button(root, text="Record Frame", bg="green", fg="white", 
                         command=animation_record_frame, font=("Arial", 10))
    ui_buttons.append(b_record)
    canvas.create_window(x_offset + 50, btn_y, window=b_record)
    x_offset += 120

    # Prev Frame
    b_prev = tk.Button(root, text="< Prev", bg="blue", fg="white", 
                       command=animation_prev_frame, font=("Arial", 10))
    ui_buttons.append(b_prev)
    canvas.create_window(x_offset + 30, btn_y, window=b_prev)
    x_offset += 60
    
    # Frame Index Display
    # Ensure this is always defined or updated correctly
    frame_index_text_id = canvas.create_text(x_offset + 40, btn_y, text="Frame: 1/1", 
                                             font=("Arial", 12, "bold"), fill="black", tags=("frame_display", "anim_ui",))
    x_offset += 80
    
    # Next Frame
    b_next = tk.Button(root, text="Next >", bg="blue", fg="white", 
                       command=animation_next_frame, font=("Arial", 10))
    ui_buttons.append(b_next)
    canvas.create_window(x_offset + 30, btn_y, window=b_next)
    x_offset += 60
    
    # Play/Stop
    b_toggle = tk.Button(root, text="Play", bg="red", fg="white", 
                         command=animation_toggle_play, font=("Arial", 10))
    ui_buttons.append(b_toggle)
    canvas.create_window(x_offset + 50, btn_y, window=b_toggle, tags=("anim_toggle_btn",))
    x_offset += 120

    # Clear All
    b_clear = tk.Button(root, text="Clear All", bg="gray", fg="black", 
                        command=animation_clear_all, font=("Arial", 10))
    ui_buttons.append(b_clear)
    canvas.create_window(WIDTH - 50, btn_y, window=b_clear)

    # Initial Shapes (for manipulation)
    canvas.create_oval(WIDTH//2 - 20, HEIGHT//2 - 20, WIDTH//2 + 20, HEIGHT//2 + 20, 
                       fill="purple", tags=("anim_shape", "movable"))
                       
    canvas.create_rectangle(WIDTH//2 - 80, HEIGHT//2 + 50, WIDTH//2 - 40, HEIGHT//2 + 90, 
                           fill="orange", tags=("anim_shape", "movable"))

    # Bind shape movement (drag and drop)
    canvas.tag_bind("movable", "<Button-1>", animation_drag_start)
    canvas.tag_bind("movable", "<B1-Motion>", animation_drag_motion)
    canvas.tag_bind("movable", "<ButtonRelease-1>", animation_drag_end)
    root.bind("<Escape>",to_menu) # No highscore for animation

    # Record the initial frame
    animation_record_frame()

def update_frame_display():
    """Updates the 'Frame: X/Y' text on the canvas."""
    global frame_index_text_id
    total_frames = max(1, len(frames))
    display_index = current_frame_index + 1
    # Check if frame_index_text_id exists before configuring
    if frame_index_text_id:
        canvas.itemconfigure(frame_index_text_id, text=f"Frame: {display_index}/{total_frames}")

def animation_clear_display():
    """Clears non-UI shapes from the canvas."""
    for item in canvas.find_withtag("anim_shape"):
        canvas.delete(item)

def animation_load_frame(index):
    """Loads a specific frame index onto the canvas."""
    global current_frame_index
    if not frames or index < 0 or index >= len(frames): return

    current_frame_index = index
    animation_clear_display()
    
    frame_data = frames[index]
    
    for _, data in frame_data.items():
        if data['type'] == 'oval':
            item = canvas.create_oval(*data['coords'], fill=data['fill'], tags=("anim_shape", "movable"))
        elif data['type'] == 'rectangle':
            item = canvas.create_rectangle(*data['coords'], fill=data['fill'], tags=("anim_shape", "movable"))
            
        # Bind events to the newly created shapes
        canvas.tag_bind(item, "<Button-1>", animation_drag_start)
        canvas.tag_bind(item, "<B1-Motion>", animation_drag_motion)
        canvas.tag_bind(item, "<ButtonRelease-1>", animation_drag_end)
        
    # Ensure UI is on top
    canvas.tag_raise("anim_ui_bg")
    canvas.tag_raise("frame_display")
    
    update_frame_display()


def animation_record_frame():
    """Captures the current state of 'anim_shape' objects and saves it as a new frame."""
    global frames, current_frame_index
    
    current_frame_state = {}
    
    # Collect data on all currently displayed movable shapes
    for item_id in canvas.find_withtag("anim_shape"):
        try:
            item_type = canvas.type(item_id)
            coords = canvas.coords(item_id)
            fill_color = canvas.itemcget(item_id, "fill")
            
            # Save relevant data for reconstruction
            current_frame_state[item_id] = {
                'type': item_type,
                'coords': coords,
                'fill': fill_color,
                # Add more properties if needed (e.g., outline, width)
            }
        except tk.TclError:
            continue # Skip deleted items

    if not current_frame_state and frames:
        # Prevent recording an empty frame if shapes were deleted, unless it's the first frame
        return

    # If the animation is playing, stop it first
    animation_toggle_play(stop_only=True)

    # Insert the new frame after the current one
    frames.insert(current_frame_index + 1, current_frame_state)
    current_frame_index += 1
    
    # Reload to ensure the canvas reflects the saved state and updates the display
    animation_load_frame(current_frame_index)


def animation_prev_frame():
    animation_toggle_play(stop_only=True)
    new_index = (current_frame_index - 1)
    if new_index >= 0:
        animation_load_frame(new_index)

def animation_next_frame():
    animation_toggle_play(stop_only=True)
    new_index = (current_frame_index + 1)
    if new_index < len(frames):
        animation_load_frame(new_index)

def animation_toggle_play(stop_only=False):
    global animation_running, after_ids
    
    # Find the Play/Stop button widget
    toggle_btn_window = canvas.find_withtag("anim_toggle_btn")
    toggle_btn = None
    if toggle_btn_window:
         # Assuming the window ID is correct, find the actual button object
        for btn in ui_buttons:
            # Check if this button is the one associated with the window on the canvas
            try:
                # Get the window info of the button and check if it matches the canvas item ID
                if str(btn) == canvas.itemcget(toggle_btn_window[0], "window"):
                    toggle_btn = btn
                    break
            except tk.TclError:
                continue

    if animation_running or stop_only:
        # Stop animation
        animation_running = False
        for aid in after_ids:
            try: root.after_cancel(aid)
            except: pass
        after_ids.clear()
        
        if toggle_btn: toggle_btn.config(text="Play", bg="red")
        
        # Ensure the canvas shows the last stopped frame
        if frames: animation_load_frame(current_frame_index) 
        
    elif not frames:
        print("Cannot play: No frames recorded. Move shapes and click 'Record Frame'.")
        return
        
    else:
        # Start animation
        animation_running = True
        if toggle_btn: toggle_btn.config(text="Stop", bg="orange")
        animation_update_loop()

def animation_update_loop():
    global current_frame_index
    if state != "animation" or not animation_running: 
        return

    # Cycle to the next frame
    current_frame_index = (current_frame_index + 1) % len(frames)
    
    # Load and display the new frame
    animation_load_frame(current_frame_index)
    
    # Continue the loop
    aid = root.after(100, animation_update_loop) # Playback speed (10 FPS)
    after_ids.append(aid)

def animation_clear_all():
    global frames, current_frame_index
    animation_toggle_play(stop_only=True)
    frames = []
    current_frame_index = 0
    animation_clear_display()
    update_frame_display()
    
    # Recreate default movable shapes
    canvas.create_oval(WIDTH//2 - 20, HEIGHT//2 - 20, WIDTH//2 + 20, HEIGHT//2 + 20, 
                       fill="purple", tags=("anim_shape", "movable"))
                       
    canvas.create_rectangle(WIDTH//2 - 80, HEIGHT//2 + 50, WIDTH//2 - 40, HEIGHT//2 + 90, 
                           fill="orange", tags=("anim_shape", "movable"))
    
    animation_record_frame() # Record the new initial state
    

# --- Drag and Drop Logic for 'movable' shapes ---
def animation_drag_start(event):
    global drag_data
    if state != "animation" or animation_running: return # Can only move shapes when paused
    
    # Identify the movable item clicked (using current item, which is the top one)
    item = canvas.find_withtag(tk.CURRENT)
    if not item: return
    
    # Ensure the item is on the canvas (not a UI button)
    if item and "movable" in canvas.gettags(item[0]):
        drag_data["item"] = item[0]
        drag_data["x"] = event.x
        drag_data["y"] = event.y

def animation_drag_motion(event):
    global drag_data
    if state != "animation" or animation_running or drag_data["item"] is None: return

    # Calculate difference
    dx = event.x - drag_data["x"]
    dy = event.y - drag_data["y"]
    
    # Move the item
    try:
        canvas.move(drag_data["item"], dx, dy)
    except tk.TclError:
        # Handle case where item might have been deleted mid-drag
        drag_data["item"] = None
        return
    
    # Update last coordinates
    drag_data["x"] = event.x
    drag_data["y"] = event.y

def animation_drag_end(event):
    global drag_data
    # Drag operation is complete. Reset drag data.
    if drag_data["item"] is not None:
        print(f"Shape {drag_data['item']} moved. Remember to click 'Record Frame' to save!")
    drag_data["item"] = None
    drag_data["x"] = 0
    drag_data["y"] = 0


# ---------- Start the application ----------
show_menu()
root.mainloop()


