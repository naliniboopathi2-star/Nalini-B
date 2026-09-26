import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from datetime import datetime
import urllib.request
import urllib.parse
import json
import threading
import joblib
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import webbrowser  # ADDED: To open GPS map links


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
MODEL_FILE = BASE_DIR / "load_ai_model.pkl"


# ============================================================
# LOAD AI MODEL
# ============================================================

try:
    package = joblib.load(MODEL_FILE)

    model = package["model"]
    FEATURES = package["features"]

    MODEL_MAX_LOAD = float(package.get("max_load_w", 2500))

    MAE = float(package.get("mae", 0))
    RMSE = float(package.get("rmse", 0))
    R2 = float(package.get("r2", 0))

except Exception as e:
    raise SystemExit(
        "AI model could not be loaded.\n\n"
        "Please run train_model.py first.\n\n"
        f"Error:\n{e}"
    )


# ============================================================
# MAIN WINDOW
# ============================================================

root = tk.Tk()
root.title("AI Smart Electrical Load Monitor & Prediction")
root.geometry("1450x900")
root.configure(bg="#101820")


# ============================================================
# VARIABLES
# ============================================================

voltage_var = tk.StringVar(value="230")
current_var = tk.StringVar(value="5")
max_load_var = tk.StringVar(value=str(int(MODEL_MAX_LOAD)))

current_power_var = tk.StringVar(value="0 W")
ai_forecast_var = tk.StringVar(value="0 W")
load_percent_var = tk.StringVar(value="0 %")

actual_status_var = tk.StringVar(value="NORMAL")
predictive_status_var = tk.StringVar(value="NORMAL")

trend_var = tk.StringVar(value="STABLE")
difference_var = tk.StringVar(value="0 W")

analysis_current_var = tk.StringVar(value="0 W")
analysis_ai_var = tk.StringVar(value="0 W")
analysis_limit_var = tk.StringVar(value="0 W")
analysis_remaining_var = tk.StringVar(value="0 W")
analysis_trend_var = tk.StringVar(value="STABLE")
analysis_forecast_change_var = tk.StringVar(value="0 %")

# ============================================================
# ESP8266 / DHT11 VARIABLES
# ============================================================

# Change this to the IP address shown by your ESP8266 Serial Monitor.
ESP8266_IP = "10.165.92.205"

# DHT11 values received from ESP8266.
temperature_var = tk.StringVar(value="-- C")
humidity_var = tk.StringVar(value="-- %")
esp_status_var = tk.StringVar(value="ESP8266: CONNECTING...")

# Keep the last received values available to the dashboard.
latest_temperature = None
latest_humidity = None

# Prevent the same warning/critical message from being sent repeatedly
# while the user is pressing PREDICT LOAD.
last_sent_alert = None


# ============================================================
# HISTORY
# ============================================================

actual_history = []
ai_history = []
time_history = []

previous_power = 0.0


# ============================================================
# COLORS
# ============================================================

BG = "#101820"
PANEL = "#17232d"
PANEL2 = "#1d2d38"
TEXT = "#ffffff"
MUTED = "#a9bac5"
GREEN = "#35d07f"
YELLOW = "#ffd166"
RED = "#ff5c5c"
BLUE = "#4dabf7"
PURPLE = "#b197fc"


# ============================================================
# TITLE
# ============================================================

title_frame = tk.Frame(root, bg=BG)
title_frame.pack(fill="x", padx=20, pady=(15, 5))

tk.Label(
    title_frame,
    text="AI SMART ELECTRICAL LOAD MONITOR",
    font=("Arial", 25, "bold"),
    bg=BG,
    fg=TEXT
).pack()

tk.Label(
    title_frame,
    text="Real-Time Load Calculation + Machine Learning Forecast",
    font=("Arial", 12),
    bg=BG,
    fg=MUTED
).pack(pady=(2, 5))


# ============================================================
# INPUT FRAME
# ============================================================

input_frame = tk.Frame(root, bg=PANEL)
input_frame.pack(fill="x", padx=20, pady=10)

tk.Label(
    input_frame,
    text="Voltage (V)",
    font=("Arial", 11, "bold"),
    bg=PANEL,
    fg=TEXT
).grid(row=0, column=0, padx=10, pady=12)

voltage_entry = tk.Entry(
    input_frame,
    textvariable=voltage_var,
    width=12,
    font=("Arial", 12)
)
voltage_entry.grid(row=0, column=1, padx=5)


tk.Label(
    input_frame,
    text="Current (A)",
    font=("Arial", 11, "bold"),
    bg=PANEL,
    fg=TEXT
).grid(row=0, column=2, padx=10)

current_entry = tk.Entry(
    input_frame,
    textvariable=current_var,
    width=12,
    font=("Arial", 12)
)
current_entry.grid(row=0, column=3, padx=5)


tk.Label(
    input_frame,
    text="Maximum Load (W)",
    font=("Arial", 11, "bold"),
    bg=PANEL,
    fg=TEXT
).grid(row=0, column=4, padx=10)

max_load_entry = tk.Entry(
    input_frame,
    textvariable=max_load_var,
    width=12,
    font=("Arial", 12)
)
max_load_entry.grid(row=0, column=5, padx=5)


# ============================================================
# FUNCTIONS & ACTIONS
# ============================================================

def open_gps_map():
    """Opens a demo GPS map location link in the default web browser."""
    # Demo coordinates (e.g., Smart Grid Substation / Demo Facility location)
    demo_lat = 11.6643
    demo_lon = 78.1460
    maps_url = f"https://www.google.com/maps/search/?api=1&query={demo_lat},{demo_lon}"
    webbrowser.open(maps_url)


def read_esp8266_sensor():
    """Read DHT11 and ESP8266 status through the local Wi-Fi API."""
    global latest_temperature, latest_humidity

    try:
        url = f"http://{ESP8266_IP}/sensor"
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "AI-Smart-Electrical-Dashboard"}
        )

        with urllib.request.urlopen(request, timeout=3) as response:
            data = json.loads(response.read().decode("utf-8"))

        latest_temperature = float(data.get("temperature", 0.0))
        latest_humidity = float(data.get("humidity", 0.0))

        return latest_temperature, latest_humidity, True

    except Exception as e:
        print("ESP8266 sensor connection error:", e)
        return None, None, False


def update_environment_dashboard():
    """Poll ESP8266 every 3 seconds without freezing the Tkinter GUI."""

    def worker():
        temperature, humidity, connected = read_esp8266_sensor()

        def update_gui():
            if connected:
                temperature_var.set(f"{temperature:.1f} C")
                humidity_var.set(f"{humidity:.1f} %")
                esp_status_var.set(f"ESP8266: ONLINE  |  {ESP8266_IP}")
                esp_status_label.config(fg=GREEN)
            else:
                temperature_var.set("OFFLINE")
                humidity_var.set("OFFLINE")
                esp_status_var.set(f"ESP8266: OFFLINE  |  {ESP8266_IP}")
                esp_status_label.config(fg=RED)

            root.after(3000, update_environment_dashboard)

        root.after(0, update_gui)

    threading.Thread(target=worker, daemon=True).start()


def send_alert_to_esp8266(status, power, limit, forecast):
    """Send the Python AI alert and electrical values to ESP8266."""
    global last_sent_alert

    alert_key = str(status)
    if alert_key == last_sent_alert and alert_key != "NORMAL":
        return

    def worker():
        global last_sent_alert

        try:
            params = urllib.parse.urlencode({
                "status": status,
                "power": f"{power:.1f}",
                "limit": f"{limit:.1f}",
                "forecast": f"{forecast:.1f}",
                "time": datetime.now().strftime("%H:%M:%S")
            })

            url = f"http://{ESP8266_IP}/alert?{params}"

            with urllib.request.urlopen(url, timeout=3) as response:
                response.read()

            last_sent_alert = alert_key
            print(f"ESP8266 alert sent: {status}")

        except Exception as e:
            print("ESP8266 alert send error:", e)

    threading.Thread(target=worker, daemon=True).start()


def clear_history():
    global previous_power, last_sent_alert

    actual_history.clear()
    ai_history.clear()
    time_history.clear()

    previous_power = 0.0
    last_sent_alert = None

    current_power_var.set("0 W")
    ai_forecast_var.set("0 W")
    load_percent_var.set("0 %")

    actual_status_var.set("NORMAL")
    predictive_status_var.set("NORMAL")

    trend_var.set("STABLE")
    difference_var.set("0 W")

    analysis_current_var.set("0 W")
    analysis_ai_var.set("0 W")
    analysis_limit_var.set("0 W")
    analysis_remaining_var.set("0 W")
    analysis_trend_var.set("STABLE")
    analysis_forecast_change_var.set("0 %")

    update_graph()


def get_status(power, limit):
    warning_limit = limit * 0.80

    if power >= limit:
        return "CRITICAL"

    if power >= warning_limit:
        return "WARNING"

    return "NORMAL"


def get_trend(current, prediction):
    if prediction > current * 1.03:
        return "INCREASING"

    if prediction < current * 0.97:
        return "DECREASING"

    return "STABLE"


def show_status_popup(actual_status, predictive_status):

    if actual_status == "CRITICAL":
        messagebox.showerror(
            "CRITICAL LOAD",
            "Actual electrical load has crossed the maximum limit!"
        )

    elif predictive_status == "CRITICAL":
        messagebox.showwarning(
            "AI PREDICTIVE WARNING",
            "AI predicts that the electrical load may cross "
            "the maximum limit within the next 5 minutes."
        )

    elif actual_status == "WARNING":
        messagebox.showwarning(
            "HIGH LOAD",
            "Current electrical load has entered the warning region."
        )

    elif predictive_status == "WARNING":
        messagebox.showinfo(
            "AI EARLY WARNING",
            "AI predicts increasing electrical load."
        )


def predict_load():

    global previous_power

    try:

        voltage = float(voltage_var.get())
        current = float(current_var.get())
        max_load = float(max_load_var.get())

        if voltage <= 0:
            raise ValueError("Voltage must be greater than zero.")

        if current < 0:
            raise ValueError("Current cannot be negative.")

        if max_load <= 0:
            raise ValueError("Maximum load must be greater than zero.")

        current_power = voltage * current

        now = datetime.now()

        hour = now.hour
        minute = now.minute
        day_of_week = now.weekday()

        if previous_power == 0:
            previous_power_for_model = current_power
        else:
            previous_power_for_model = previous_power

        power_change = current_power - previous_power_for_model
        load_percentage = (current_power / max_load) * 100

        input_data = pd.DataFrame(
            [[
                voltage,
                current,
                current_power,
                load_percentage,
                previous_power_for_model,
                power_change,
                hour,
                minute,
                day_of_week
            ]],
            columns=FEATURES
        )

        raw_ai_prediction = float(model.predict(input_data)[0])
        ai_prediction = max(0.0, raw_ai_prediction)

        actual_status = get_status(current_power, max_load)
        predictive_status = get_status(ai_prediction, max_load)
        trend = get_trend(current_power, ai_prediction)
        prediction_difference = ai_prediction - current_power

        if actual_status == "CRITICAL" or predictive_status == "CRITICAL":
            esp_alert_status = "CRITICAL"
        elif actual_status == "WARNING" or predictive_status == "WARNING":
            esp_alert_status = "WARNING"
        else:
            esp_alert_status = "NORMAL"

        send_alert_to_esp8266(
            esp_alert_status,
            current_power,
            max_load,
            ai_prediction
        )

        if current_power != 0:
            forecast_change_percent = (
                prediction_difference / current_power
            ) * 100
        else:
            forecast_change_percent = 0

        current_power_var.set(f"{current_power:,.0f} W")
        ai_forecast_var.set(f"{ai_prediction:,.0f} W")
        load_percent_var.set(f"{load_percentage:.1f} %")
        actual_status_var.set(actual_status)
        predictive_status_var.set(predictive_status)
        trend_var.set(trend)
        difference_var.set(f"{prediction_difference:+,.0f} W")

        analysis_current_var.set(f"{current_power:,.0f} W")
        analysis_ai_var.set(f"{ai_prediction:,.0f} W")
        analysis_limit_var.set(f"{max_load:,.0f} W")
        remaining_capacity = max_load - ai_prediction
        analysis_remaining_var.set(f"{remaining_capacity:+,.0f} W")
        analysis_trend_var.set(trend)
        analysis_forecast_change_var.set(f"{forecast_change_percent:+.1f} %")

        actual_history.append(current_power)
        ai_history.append(ai_prediction)
        time_history.append(datetime.now().strftime("%H:%M:%S"))

        if len(actual_history) > 30:
            actual_history.pop(0)
            ai_history.pop(0)
            time_history.pop(0)

        previous_power = current_power
        update_graph()

        if (
            actual_status == "CRITICAL"
            or predictive_status == "CRITICAL"
            or actual_status == "WARNING"
            or predictive_status == "WARNING"
        ):
            show_status_popup(actual_status, predictive_status)

    except ValueError as e:
        messagebox.showerror("Input Error", str(e))
    except Exception as e:
        messagebox.showerror("Prediction Error", f"Something went wrong:\n\n{e}")


def update_graph():
    ax.clear()

    if len(actual_history) > 0:
        x = list(range(1, len(actual_history) + 1))

        ax.plot(x, actual_history, marker="o", linewidth=2.5, label="ACTUAL LOAD")
        ax.plot(x, ai_history, marker="s", linewidth=2.5, linestyle="--", label="AI FORECAST")

        try:
            max_load = float(max_load_var.get())
            ax.axhline(max_load, linewidth=2, linestyle=":", label="MAXIMUM LIMIT")
        except:
            pass

        ax.fill_between(x, actual_history, alpha=0.08)
        ax.set_xticks(x)

        if len(time_history) <= 10:
            ax.set_xticklabels(time_history, rotation=35, ha="right")
        else:
            step = max(1, len(time_history) // 8)
            selected_x = x[::step]
            selected_labels = time_history[::step]
            ax.set_xticks(selected_x)
            ax.set_xticklabels(selected_labels, rotation=35, ha="right")

    ax.set_title(
        "ACTUAL LOAD VS AI 5-MINUTE FORECAST",
        fontsize=14,
        fontweight="bold"
    )

    ax.set_xlabel("Prediction Sequence")
    ax.set_ylabel("Power (W)")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="upper left")
    fig.tight_layout()
    canvas.draw()


# ============================================================
# BUTTONS & CONTROLS
# ============================================================

predict_button = tk.Button(
    input_frame,
    text="PREDICT LOAD",
    command=predict_load,
    font=("Arial", 11, "bold"),
    width=14,
    bg=GREEN,
    fg="black",
    activebackground=GREEN,
    cursor="hand2"
)
predict_button.grid(row=0, column=6, padx=10)


map_button = tk.Button(
    input_frame,
    text="VIEW GPS MAP",
    command=open_gps_map,
    font=("Arial", 11, "bold"),
    width=14,
    bg=BLUE,
    fg="black",
    activebackground=BLUE,
    cursor="hand2"
)
map_button.grid(row=0, column=7, padx=10)


reset_button = tk.Button(
    input_frame,
    text="RESET",
    command=clear_history,
    font=("Arial", 11, "bold"),
    width=10,
    bg=RED,
    fg="white",
    activebackground=RED,
    cursor="hand2"
)
reset_button.grid(row=0, column=8, padx=5)


# ============================================================
# KPI FRAME
# ============================================================

kpi_frame = tk.Frame(root, bg=BG)
kpi_frame.pack(fill="x", padx=20, pady=5)


def create_kpi(parent, title, variable, column):
    frame = tk.Frame(parent, bg=PANEL2, width=250, height=110)
    frame.grid(row=0, column=column, padx=7, sticky="nsew")
    frame.grid_propagate(False)

    tk.Label(
        frame,
        text=title,
        font=("Arial", 10, "bold"),
        bg=PANEL2,
        fg=MUTED
    ).pack(pady=(12, 3))

    tk.Label(
        frame,
        textvariable=variable,
        font=("Arial", 21, "bold"),
        bg=PANEL2,
        fg=TEXT
    ).pack()


for i in range(5):
    kpi_frame.grid_columnconfigure(i, weight=1)

create_kpi(kpi_frame, "CURRENT POWER", current_power_var, 0)
create_kpi(kpi_frame, "AI FORECAST", ai_forecast_var, 1)
create_kpi(kpi_frame, "LOAD UTILIZATION", load_percent_var, 2)
create_kpi(kpi_frame, "ACTUAL STATUS", actual_status_var, 3)
create_kpi(kpi_frame, "AI PREDICTIVE STATUS", predictive_status_var, 4)


# ============================================================
# ENVIRONMENTAL MONITORING - DHT11 VIA ESP8266
# ============================================================

environment_frame = tk.Frame(root, bg=PANEL)
environment_frame.pack(fill="x", padx=20, pady=(5, 10))

environment_frame.grid_columnconfigure(0, weight=1)
environment_frame.grid_columnconfigure(1, weight=1)
environment_frame.grid_columnconfigure(2, weight=1)


def create_environment_card(parent, title, variable, column):
    frame = tk.Frame(parent, bg=PANEL2, height=105)
    frame.grid(row=0, column=column, padx=7, pady=7, sticky="nsew")
    frame.grid_propagate(False)

    tk.Label(
        frame,
        text=title,
        font=("Arial", 10, "bold"),
        bg=PANEL2,
        fg=MUTED
    ).pack(pady=(10, 3))

    tk.Label(
        frame,
        textvariable=variable,
        font=("Arial", 21, "bold"),
        bg=PANEL2,
        fg=TEXT
    ).pack()


create_environment_card(environment_frame, "DHT11 TEMPERATURE", temperature_var, 0)
create_environment_card(environment_frame, "DHT11 HUMIDITY", humidity_var, 1)

esp_status_label = tk.Label(
    environment_frame,
    textvariable=esp_status_var,
    font=("Arial", 10, "bold"),
    bg=PANEL2,
    fg=YELLOW
)
esp_status_label.grid(row=0, column=2, padx=10, pady=10, sticky="nsew")


# ============================================================
# MAIN CONTENT
# ============================================================

content_frame = tk.Frame(root, bg=BG)
content_frame.pack(fill="both", expand=True, padx=20, pady=10)

graph_frame = tk.Frame(content_frame, bg=PANEL)
graph_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))

fig, ax = plt.subplots(figsize=(8, 5))
fig.patch.set_facecolor(PANEL)
ax.set_facecolor(PANEL)

ax.tick_params(colors=TEXT)
ax.xaxis.label.set_color(TEXT)
ax.yaxis.label.set_color(TEXT)
ax.title.set_color(TEXT)

for spine in ax.spines.values():
    spine.set_color("#607d8b")

canvas = FigureCanvasTkAgg(fig, master=graph_frame)
canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)


# ------------------------------------------------------------
# ANALYSIS PANEL
# ------------------------------------------------------------

analysis_frame = tk.Frame(content_frame, bg=PANEL, width=380)
analysis_frame.pack(side="right", fill="y")
analysis_frame.pack_propagate(False)

tk.Label(
    analysis_frame,
    text="AI ANALYSIS",
    font=("Arial", 17, "bold"),
    bg=PANEL,
    fg=TEXT
).pack(pady=(15, 10))


def analysis_row(parent, label, variable):
    row = tk.Frame(parent, bg=PANEL)
    row.pack(fill="x", padx=15, pady=7)

    tk.Label(
        row,
        text=label,
        font=("Arial", 10, "bold"),
        bg=PANEL,
        fg=MUTED,
        anchor="w"
    ).pack(side="left")

    tk.Label(
        row,
        textvariable=variable,
        font=("Arial", 11, "bold"),
        bg=PANEL,
        fg=TEXT,
        anchor="e"
    ).pack(side="right")


analysis_row(analysis_frame, "Current Power", analysis_current_var)
analysis_row(analysis_frame, "AI 5-Min Forecast", analysis_ai_var)
analysis_row(analysis_frame, "Maximum Limit", analysis_limit_var)
analysis_row(analysis_frame, "AI Remaining Capacity", analysis_remaining_var)
analysis_row(analysis_frame, "AI Trend", analysis_trend_var)
analysis_row(analysis_frame, "Forecast Change", analysis_forecast_change_var)


# ============================================================
# EXPLANATION BOX
# ============================================================

tk.Label(
    analysis_frame,
    text="HOW THE AI WORKS",
    font=("Arial", 14, "bold"),
    bg=PANEL,
    fg=BLUE
).pack(pady=(25, 8))

explanation = (
    "1. Current electrical power is calculated\n"
    "   using Voltage × Current.\n\n"
    "2. Historical electrical data is used\n"
    "   to train the Random Forest model.\n\n"
    "3. The AI analyzes present load conditions\n"
    "   and historical load behavior.\n\n"
    "4. It forecasts the expected power\n"
    "   for the next 5 minutes.\n\n"
    "5. The forecast is compared with the\n"
    "   maximum allowable load.\n\n"
    "ACTUAL = What is happening now\n"
    "AI FORECAST = What may happen next"
)

tk.Label(
    analysis_frame,
    text=explanation,
    font=("Arial", 10),
    bg=PANEL,
    fg=TEXT,
    justify="left",
    anchor="w"
).pack(padx=18, fill="x")


# ============================================================
# MODEL PERFORMANCE
# ============================================================

performance_frame = tk.Frame(root, bg=PANEL)
performance_frame.pack(fill="x", padx=20, pady=(0, 15))

tk.Label(
    performance_frame,
    text="AI MODEL PERFORMANCE",
    font=("Arial", 12, "bold"),
    bg=PANEL,
    fg=TEXT
).pack(side="left", padx=15, pady=10)

tk.Label(
    performance_frame,
    text=f"MAE: {MAE:.2f} W",
    font=("Arial", 10, "bold"),
    bg=PANEL,
    fg=GREEN
).pack(side="left", padx=15)

tk.Label(
    performance_frame,
    text=f"RMSE: {RMSE:.2f} W",
    font=("Arial", 10, "bold"),
    bg=PANEL,
    fg=YELLOW
).pack(side="left", padx=15)

tk.Label(
    performance_frame,
    text=f"R²: {R2:.3f}",
    font=("Arial", 10, "bold"),
    bg=PANEL,
    fg=BLUE
).pack(side="left", padx=15)

tk.Label(
    performance_frame,
    text="Model: Random Forest Regression",
    font=("Arial", 10, "bold"),
    bg=PANEL,
    fg=PURPLE
).pack(side="right", padx=15)


# ============================================================
# INITIAL GRAPH
# ============================================================

update_graph()

# Start automatic DHT11 / ESP8266 monitoring.
update_environment_dashboard()


# ============================================================
# START GUI
# ============================================================

root.mainloop()