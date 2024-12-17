import { createContext, useState, useContext } from "react";

const BLEContext = createContext(null);

// ESP32 Environmental Sensing Service UUID
const ENV_SENSE_UUID = 0x181a;
const TEMP_CHAR_UUID = 0x2a6e;
const DISTANCE_CHAR_UUID = 0x2a5b; // Add distance characteristic UUID
const INTERVAL_CHAR_UUID = 0x2a24; // Add interval characteristic UUID
const HUMIDITY_CHAR_UUID = 0x2a6f;
const BATT_SVC_UUID = 0x180f;
const BATT_LEVEL_CHAR_UUID = 0x2a19;

export const BLEProvider = ({ children }) => {
    const [device, setDevice] = useState(null);
    const [isConnected, setIsConnected] = useState(false);
    const [temperature, setTemperature] = useState(null);
    const [distance, setDistance] = useState(null); // Add distance state
    const [interval, setInterval] = useState(null); // Add interval state
    const [lastReceived, setLastReceived] = useState(null); // Add last received state
    const [humidity, setHumidity] = useState(null);
    const [batteryLevel, setBatteryLevel] = useState(null);

    const registerBackgroundSync = async () => {
        try {
            if ("serviceWorker" in navigator && "periodicSync" in navigator.serviceWorker) {
                const registration = await navigator.serviceWorker.ready;
                await registration.periodicSync.register("ble-sync", {
                    minInterval: 60 * 1000, // Minimum 1 minute
                });
            }
        } catch (error) {
            console.error("Background sync registration failed:", error);
        }
    };

    const connectToDevice = async () => {
        try {
            console.log("Requesting Bluetooth Device...");
            const device = await navigator.bluetooth.requestDevice({
                acceptAllDevices: true,
                optionalServices: [ENV_SENSE_UUID, BATT_SVC_UUID], // Add battery service
            });

            console.log("Connecting to GATT Server...");
            const server = await device.gatt.connect();

            // Request pairing if device is not bonded
            if (!device.gatt.connected) {
                console.log("Initiating pairing...");
                await device.gatt.device.watchAdvertisements();
            }

            // Add security event listeners
            device.addEventListener("advertisementreceived", (event) => {
                console.log("Advertisement received:", event);
            });

            device.addEventListener("characteristicvaluechanged", (event) => {
                // This will trigger for encrypted characteristics
                console.log("Secure characteristic value changed");
            });

            console.log("Getting Environmental Service...");
            const envService = await server.getPrimaryService(ENV_SENSE_UUID);
            const battService = await server.getPrimaryService(BATT_SVC_UUID);

            // Handle temperature characteristic
            console.log("Getting Temperature Characteristic...");
            const tempCharacteristic = await envService.getCharacteristic(TEMP_CHAR_UUID);

            // Handle distance characteristic
            console.log("Getting Distance Characteristic...");
            const distanceCharacteristic = await envService.getCharacteristic(DISTANCE_CHAR_UUID);

            // Handle interval characteristic
            console.log("Getting Interval Characteristic...");
            const intervalCharacteristic = await envService.getCharacteristic(INTERVAL_CHAR_UUID);

            // Handle humidity characteristic
            console.log("Getting Humidity Characteristic...");
            const humidityCharacteristic = await envService.getCharacteristic(HUMIDITY_CHAR_UUID);
            await humidityCharacteristic.startNotifications();
            humidityCharacteristic.addEventListener("characteristicvaluechanged", (event) => {
                const value = event.target.value;
                const humid = value.getUint16(0, true) / 100;
                const timestamp = new Date().toLocaleString();

                const data = { humidity: humid, timestamp };
                localStorage.setItem("latest_humidity", JSON.stringify(data));

                console.log("Received encrypted humidity:", humid);
                setHumidity(humid);
                setLastReceived(timestamp);
            });

            // Handle battery level characteristic
            console.log("Getting Battery Level Characteristic...");
            const batteryCharacteristic = await battService.getCharacteristic(BATT_LEVEL_CHAR_UUID);
            await batteryCharacteristic.startNotifications();
            batteryCharacteristic.addEventListener("characteristicvaluechanged", (event) => {
                const value = event.target.value;
                const level = value.getUint8(0);
                const timestamp = new Date().toLocaleString();

                const data = { batteryLevel: level, timestamp };
                localStorage.setItem("latest_battery", JSON.stringify(data));

                console.log("Received battery level:", level);
                setBatteryLevel(level);
                setLastReceived(timestamp);
            });

            // Enable notifications for temperature
            await tempCharacteristic.startNotifications();
            tempCharacteristic.addEventListener("characteristicvaluechanged", (event) => {
                const value = event.target.value;
                const temp = value.getInt16(0, true) / 100;
                const timestamp = new Date().toLocaleString();

                // Store data for background sync
                const data = { temperature: temp, timestamp };
                localStorage.setItem("latest_temperature", JSON.stringify(data));

                console.log("Received encrypted temperature:", temp);
                setTemperature(temp);
                setLastReceived(timestamp);
            });

            // Enable notifications for distance
            await distanceCharacteristic.startNotifications();
            distanceCharacteristic.addEventListener("characteristicvaluechanged", (event) => {
                const value = event.target.value;
                const dist = value.getUint16(0, true) / 10; // Convert mm to cm
                const timestamp = new Date().toLocaleString();

                // Store data for background sync
                const data = { distance: dist, timestamp };
                localStorage.setItem("latest_distance", JSON.stringify(data));

                console.log("Received encrypted distance:", dist);
                setDistance(dist);
                setLastReceived(timestamp);
            });

            // Enable notifications for interval
            await intervalCharacteristic.startNotifications();
            intervalCharacteristic.addEventListener("characteristicvaluechanged", (event) => {
                const value = event.target.value;
                const intervalMs = value.getUint32(0, true); // Get interval as uint32
                const timestamp = new Date().toLocaleString();

                // Store data for background sync
                const data = { interval: intervalMs, timestamp };
                localStorage.setItem("latest_interval", JSON.stringify(data));

                console.log("Received interval:", intervalMs);
                setInterval(intervalMs);
                setLastReceived(timestamp);
            });

            await registerBackgroundSync();

            setDevice(device);
            setIsConnected(true);

            // Handle disconnection
            device.addEventListener("gattserverdisconnected", () => {
                console.log("Disconnected - Bond status may need refresh");
                setIsConnected(false);
                setTemperature(null);
                setDistance(null); // Reset distance on disconnection
                setInterval(null); // Reset interval on disconnection
                setHumidity(null); // Reset humidity
                setBatteryLevel(null); // Reset battery
            });
        } catch (error) {
            console.error("Connection error:", error);
            if (error.message.includes("security")) {
                console.log("Security error - may need to forget device and repair");
            }
        }
    };

    const disconnect = () => {
        if (device) {
            device.gatt.disconnect();
            setDevice(null);
            setIsConnected(false);
        }
    };

    return (
        <BLEContext.Provider
            value={{
                device,
                isConnected,
                temperature,
                distance, // Add distance to context value
                interval, // Add interval to context value
                lastReceived, // Add last received to context value
                humidity,
                batteryLevel,
                connectToDevice,
                disconnect,
            }}>
            {children}
        </BLEContext.Provider>
    );
};

export const useBLE = () => useContext(BLEContext);
