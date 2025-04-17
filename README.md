# Automated Pet Care System (APCS) - Backend

The backend server for the Automated Pet Care System, a comprehensive IoT solution for remote pet care monitoring and control.

## Overview

The APCS backend is built with Node.js and Express, using MongoDB for data storage. It provides API endpoints for the frontend application and handles MQTT communication with hardware devices.

## Directory Structure

```
backend/
├── app.js                    # Express app configuration
├── server.js                 # Server entry point
├── package.json              # Backend dependencies
├── config/                   # Server configuration
│   ├── config.js             # Environment variables
│   └── db.js                 # MongoDB connection
├── controllers/              # Route controllers
│   ├── authController.js     # Authentication logic
│   ├── sensorController.js   # Sensor data handling
│   ├── controlController.js  # Device control operations
│   └── ...
├── middleware/               # Express middleware
│   ├── authMiddleware.js     # JWT verification
│   └── errorMiddleware.js    # Error handling
├── models/                   # MongoDB schemas
│   ├── User.js               # User authentication and profile
│   ├── Device.js             # Connected devices
│   ├── SensorData.js         # Sensor readings
│   ├── Command.js            # Hardware commands
│   └── Notification.js       # User notifications
├── routes/                   # API routes
│   ├── authRoutes.js         # Authentication endpoints
│   ├── sensorRoutes.js       # Sensor data endpoints
│   ├── controlRoutes.js      # Control command endpoints
│   └── ...
└── services/                 # Backend services
    ├── socketService.js      # Socket.io implementation
    └── mqttService.js        # MQTT communication service
```

## Prerequisites

- [Node.js]
- [npm]
- [MongoDB]
- [Mosquitto MQTT client]

## Installation

1. Clone the repository:
```bash
git clone https://github.com/DavidAoGuo/APCS_backend.git
cd APCS_backend
```

2. Install dependencies:
```bash
npm install
```
## Prerequisites

- [Node.js]
- [npm]
- [MongoDB]
- [Mosquitto MQTT client]

## Installation

1. Clone the repository:
```bash
git clone https://github.com/DavidAoGuo/APCS_backend.git
cd APCS_backend
```

2. Install dependencies:
```bash
npm install
```

3. Create a `.env` file in the root directory with the following variables:
```
NODE_ENV=development
PORT=5000
MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority
JWT_SECRET=your_jwt_secret_key_here
JWT_EXPIRES_IN=1d
JWT_REFRESH_SECRET=your_refresh_token_secret_here
JWT_REFRESH_EXPIRES_IN=7d
MQTT_BROKER=mqtt://test.mosquitto.org
```

For MongoDB Atlas, replace the MONGO_URI with your connection string. A MongoDB Atlas connection string looks like this: `mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority`

4. Start the server:
```bash
# Development mode with auto-reload
npm run dev

# Production mode
npm start
```

The server will run on port 5000 (or the port specified in your .env file).

## Testing MQTT Communication

The backend communicates with hardware devices using MQTT protocol. You can test this integration with these commands:

### Simulating Sensor Data (Hardware to Backend)

```bash
mosquitto_pub -h test.mosquitto.org -t "/seniorDesign/c2s" -m "70,65,23,55"
```

Where values represent:
- 70 - Food level (%)
- 65 - Water level (%)
- 23 - Temperature (°C)
- 55 - Humidity (%)

### Monitoring Backend Commands (Backend to Hardware)

```bash
mosquitto_sub -h test.mosquitto.org -t "/seniorDesign/s2c" -v
```

## Troubleshooting

- **MongoDB Connection Issues**: Verify your MongoDB connection string in the `.env` file and ensure MongoDB is running.
- **Port Already in Use**: Change the PORT value in your `.env` file.
- **MQTT Connection Issues**: Ensure you have internet access for the public MQTT broker.