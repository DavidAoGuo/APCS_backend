const http = require('http');
const app = require('./app');
const connectDB = require('./config/db');
const setupSocketIO = require('./services/socketService');
const config = require('./config/config');
const mqttService = require('./services/mqttService');
const schedulerService = require('./services/schedulerService');

// Connect to MongoDB
connectDB();

// Create HTTP server
const server = http.createServer(app);

// Setup Socket.IO
const io = setupSocketIO(server);
console.log('Initializing MQTT service from server.js...');
mqttService.initialize();
// Clear retained messages after a short delay
setTimeout(() => {
  mqttService.clearRetainedMessages();
}, 2000);
console.log('MQTT service initialized');
if (config.NODE_ENV === 'production' || config.NODE_ENV === 'development') {
  schedulerService.initScheduler();
}
// Start server
const PORT = config.PORT;

server.listen(PORT, async () => {
  console.log(`Server running in ${config.NODE_ENV} mode on port ${PORT}`);
  
  // Initialize demo device for testing if in development mode
  if (config.NODE_ENV === 'development') {
    try {
      await initializeDemoDevice();
    } catch (error) {
      console.error('Error initializing demo device:', error);
    }
  }
});

// Function to initialize a demo device and data for testing
// Replace the existing initializeDemoDevice function
async function initializeDemoDevice() {
  const User = require('./models/User');
  const Device = require('./models/Device');
  const SensorData = require('./models/SensorData');
  
  // Check if demo user exists
  let demoUser = await User.findOne({ email: 'demo@example.com' });
  
  // Create demo user if doesn't exist
  if (!demoUser) {
    console.log('Creating demo user...');
    demoUser = await User.create({
      name: 'Demo User',
      email: 'demo@example.com',
      password: 'password123'
    });
  }
  
  // Check if demo device exists
  let demoDevice = await Device.findOne({ userId: demoUser._id });
  
  // Create demo device if doesn't exist
  if (!demoDevice) {
    console.log('Creating demo device...');
    demoDevice = await Device.create({
      userId: demoUser._id,
      name: 'Demo Pet Feeder',
      serialNumber: 'APCS-DEMO-001',
      status: 'online'
    });
    
    // Initialize sensor data only for new devices
    console.log('Initializing sensor data...');
    
    // Initial food level (70%)
    await SensorData.create({
      deviceId: demoDevice._id,
      type: 'food',
      value: 70
    });
    
    // Initial water level (65%)
    await SensorData.create({
      deviceId: demoDevice._id,
      type: 'water',
      value: 65
    });
    
    // Initial temperature (23°C)
    await SensorData.create({
      deviceId: demoDevice._id,
      type: 'temperature',
      value: 23
    });
    
    // Initial humidity (55%)
    await SensorData.create({
      deviceId: demoDevice._id,
      type: 'humidity',
      value: 55
    });
    
    console.log('Demo device initialized successfully');
  } else {
    console.log('Demo device already exists');
    
    // Check if any sensor data exists for this device
    const anySensorData = await SensorData.findOne({ deviceId: demoDevice._id });
    
    // Only initialize sensor data if none exists at all
    if (!anySensorData) {
      console.log('No sensor data found, initializing...');
      
      // Initial food level (70%)
      await SensorData.create({
        deviceId: demoDevice._id,
        type: 'food',
        value: 70
      });
      
      // Initial water level (65%)
      await SensorData.create({
        deviceId: demoDevice._id,
        type: 'water',
        value: 65
      });
      
      // Initial temperature (23°C)
      await SensorData.create({
        deviceId: demoDevice._id,
        type: 'temperature',
        value: 23
      });
      
      // Initial humidity (55%)
      await SensorData.create({
        deviceId: demoDevice._id,
        type: 'humidity',
        value: 55
      });
      
      console.log('Sensor data initialized successfully');
    } else {
      console.log('Sensor data already exists, skipping initialization');
    }
  }
}