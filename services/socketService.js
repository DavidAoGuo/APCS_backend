const socketIO = require('socket.io');
const jwt = require('jsonwebtoken');
const config = require('../config/config');
const User = require('../models/User');
const Device = require('../models/Device');
const SensorData = require('../models/SensorData');
const Notification = require('../models/Notification');
const Command = require('../models/Command');
const mqttService = require('./mqttService');


const setupSocketIO = (server) => {
  const io = socketIO(server, {
    cors: {
      origin: "*",
      methods: ["GET", "POST"]
    }
  });
  
  require('socket.io').instance = io;

  // Middleware for authentication
  io.use(async (socket, next) => {
    try {
      const token = socket.handshake.auth.token;
      
      if (!token) {
        return next(new Error('Authentication error'));
      }
      
      const decoded = jwt.verify(token, config.JWT_SECRET);
      
      const user = await User.findById(decoded.id);
      
      if (!user) {
        return next(new Error('User not found'));
      }
      
      // Attach user to socket
      socket.user = user;
      next();
    } catch (error) {
      console.error('Socket authentication error:', error);
      next(new Error('Authentication error'));
    }
  });
  
  

  io.on('connection', async (socket) => {
    console.log(`User connected: ${socket.user._id}`);
    socket.join(`user:${socket.user._id}`);

    try {
      // Get user's devices
      const devices = await Device.find({ userId: socket.user._id });
      
      if (devices.length > 0) {
        // Update device status to online
        const device = devices[0];
        device.status = 'online';
        device.lastConnected = new Date();
        await device.save();
        
        // Join device room
        socket.join(`device:${device._id}`);
        
        // Emit device status
        io.to(`device:${device._id}`).emit('deviceStatus', {
          id: device._id,
          status: device.status,
          lastConnected: device.lastConnected
        });
      }
    } catch (error) {
      console.error('Error handling socket connection:', error);
    }
    
    // Handle food dispensing
    socket.on('dispenseFood', async (data) => {
      try {
        const { amount } = data;
        
        if (!amount || amount <= 0 || amount > 100) {
          return socket.emit('error', {
            message: 'Invalid amount. Must be between 1 and 100.'
          });
        }
        
        // Get user's devices
        const devices = await Device.find({ userId: socket.user._id });
        
        if (devices.length === 0) {
          return socket.emit('error', {
            message: 'No devices found'
          });
        }
        
        const device = devices[0];
        
        // Create a command record for the hardware to process
        const command = await Command.create({
          deviceId: device._id,
          type: 'dispenseFood',
          value: amount,
          status: 'pending'
        });
        
        // Send command via MQTT
        console.log('🚀 Sending food dispense command via MQTT from socket handler');
        const mqttSent = await mqttService.sendCommand('dispenseFood', amount, device._id);
        
        if (mqttSent) {
          command.status = 'processing';
          await command.save();
          console.log(`✅ MQTT command sent successfully from socket handler: ${command._id}`);
        } else {
          console.log(`❌ MQTT command failed from socket handler: ${command._id}`);
        }
        
        // Create notification
        const notification = await Notification.create({
          userId: socket.user._id,
          title: 'Food Dispense Command Sent',
          message: `Command to dispense ${amount}% of food has been sent to the device.`,
          type: 'info'
        });
        
        // Emit notification and command status
        socket.emit('notification', notification);
        socket.emit('commandStatus', {
          id: command._id,
          type: 'dispenseFood',
          value: amount,
          status: command.status, // Use the updated status
          timestamp: command.timestamp
        });
        
        // No sensor data creation or simulation - hardware should handle this
        
      } catch (error) {
        console.error('Error dispensing food:', error);
        socket.emit('error', {
          message: 'Error sending dispense command'
        });
      }
    });
    
    // Handle water dispensing
    socket.on('dispenseWater', async (data) => {
      try {
        const { amount } = data;
        
        if (!amount || amount <= 0 || amount > 100) {
          return socket.emit('error', {
            message: 'Invalid amount. Must be between 1 and 100.'
          });
        }
        
        // Get user's devices
        const devices = await Device.find({ userId: socket.user._id });
        
        if (devices.length === 0) {
          return socket.emit('error', {
            message: 'No devices found'
          });
        }
        
        const device = devices[0];
        
        // Create a command record for the hardware to process
        const command = await Command.create({
          deviceId: device._id,
          type: 'dispenseWater',
          value: amount,
          status: 'pending'
        });
        
        // Send command via MQTT
        console.log('🚀 Sending water dispense command via MQTT from socket handler');
        const mqttSent = await mqttService.sendCommand('dispenseWater', amount, device._id);
        
        if (mqttSent) {
          command.status = 'processing';
          await command.save();
          console.log(`✅ MQTT command sent successfully from socket handler: ${command._id}`);
        } else {
          console.log(`❌ MQTT command failed from socket handler: ${command._id}`);
        }
        
        // Create notification
        const notification = await Notification.create({
          userId: socket.user._id,
          title: 'Water Dispense Command Sent',
          message: `Command to dispense ${amount}% of water has been sent to the device.`,
          type: 'info'
        });
        
        // Emit notification and command status
        socket.emit('notification', notification);
        socket.emit('commandStatus', {
          id: command._id,
          type: 'dispenseWater',
          value: amount,
          status: command.status, // Use the updated status
          timestamp: command.timestamp
        });
        
        // No sensor data creation or simulation - hardware should handle this
        
      } catch (error) {
        console.error('Error dispensing water:', error);
        socket.emit('error', {
          message: 'Error sending dispense command'
        });
      }
    });
    
    // Handle temperature setting
    socket.on('setTemperature', async (data) => {
      try {
        const { temperature } = data;
        
        if (temperature === undefined || temperature < 15 || temperature > 30) {
          return socket.emit('error', {
            message: 'Invalid temperature. Must be between 15°C and 30°C.'
          });
        }
        
        // Get user's devices
        const devices = await Device.find({ userId: socket.user._id });
        
        if (devices.length === 0) {
          return socket.emit('error', {
            message: 'No devices found'
          });
        }
        
        const device = devices[0];
        
        // Create a command record for the hardware to process
        const command = await Command.create({
          deviceId: device._id,
          type: 'setTemperature',
          value: temperature,
          status: 'pending'
        });
        
        // Send command via MQTT
        console.log('🚀 Sending temperature command via MQTT from socket handler');
        const mqttSent = await mqttService.sendCommand('setTemperature', temperature, device._id);
        
        if (mqttSent) {
          command.status = 'processing';
          await command.save();
          console.log(`✅ MQTT command sent successfully from socket handler: ${command._id}`);
        } else {
          console.log(`❌ MQTT command failed from socket handler: ${command._id}`);
        }
        
        // Create notification
        const notification = await Notification.create({
          userId: socket.user._id,
          title: 'Temperature Command Sent',
          message: `Command to set temperature to ${temperature}°C has been sent to the device.`,
          type: 'info'
        });
        
        // Emit notification and command status
        socket.emit('notification', notification);
        socket.emit('commandStatus', {
          id: command._id,
          type: 'setTemperature',
          value: temperature,
          status: command.status, // Use the updated status
          timestamp: command.timestamp
        });
        
        // No sensor data creation or simulation - hardware should handle this
        
      } catch (error) {
        console.error('Error setting temperature:', error);
        socket.emit('error', {
          message: 'Error sending temperature command'
        });
      }
    });
    
    // Handle disconnection
    socket.on('disconnect', async () => {
      console.log(`User disconnected: ${socket.user._id}`);
      
      try {
        // Get user's devices
        const devices = await Device.find({ userId: socket.user._id });
        
        if (devices.length > 0) {
          // Update device status to offline
          const device = devices[0];
          device.status = 'offline';
          await device.save();
          
          // Emit device status to other clients
          io.to(`device:${device._id}`).emit('deviceStatus', {
            id: device._id,
            status: device.status,
            lastConnected: device.lastConnected
          });
        }
      } catch (error) {
        console.error('Error handling socket disconnection:', error);
      }
    });
  });
  
  // Function for simulating sensor data updates (for testing)
  const simulateSensorUpdates = async () => {
    try {
      // Find all online devices
      const onlineDevices = await Device.find({ status: 'online' });
      
      for (const device of onlineDevices) {
        // Get latest sensor readings
        const foodData = await SensorData.findOne({ 
          deviceId: device._id, 
          type: 'food' 
        }).sort({ timestamp: -1 });
        
        const waterData = await SensorData.findOne({ 
          deviceId: device._id, 
          type: 'water' 
        }).sort({ timestamp: -1 });
        
        const temperatureData = await SensorData.findOne({ 
          deviceId: device._id, 
          type: 'temperature' 
        }).sort({ timestamp: -1 });
        
        const humidityData = await SensorData.findOne({ 
          deviceId: device._id, 
          type: 'humidity' 
        }).sort({ timestamp: -1 });
        
        // Simulate food consumption (decrease by 1-3%)
        if (foodData && foodData.value > 0) {
          const decrease = Math.random() * 3 + 1;
          const newFoodLevel = Math.max(0, foodData.value - decrease);
          
          // Create new sensor reading
          const newFoodData = await SensorData.create({
            deviceId: device._id,
            type: 'food',
            value: newFoodLevel
          });
          
          // Emit update
          io.to(`device:${device._id}`).emit('foodLevelUpdate', {
            level: newFoodLevel,
            timestamp: newFoodData.timestamp
          });
          
          // Create low food notification if needed
          if (newFoodLevel <= 20 && foodData.value > 20) {
            const notification = await Notification.create({
              userId: device.userId,
              title: 'Low Food Level',
              message: 'Food level is below 20%. Consider refilling soon.',
              type: 'warning'
            });
            
            io.to(`device:${device._id}`).emit('notification', notification);
          } else if (newFoodLevel <= 10 && foodData.value > 10) {
            const notification = await Notification.create({
              userId: device.userId,
              title: 'Critical Food Level',
              message: 'Food level is below 10%. Please refill as soon as possible.',
              type: 'danger'
            });
            
            io.to(`device:${device._id}`).emit('notification', notification);
          }
        }
        
        // Simulate water consumption (decrease by 1-5%)
        if (waterData && waterData.value > 0) {
          const decrease = Math.random() * 5 + 1;
          const newWaterLevel = Math.max(0, waterData.value - decrease);
          
          // Create new sensor reading
          const newWaterData = await SensorData.create({
            deviceId: device._id,
            type: 'water',
            value: newWaterLevel
          });
          
          // Emit update
          io.to(`device:${device._id}`).emit('waterLevelUpdate', {
            level: newWaterLevel,
            timestamp: newWaterData.timestamp
          });
          
          // Create low water notification if needed
          if (newWaterLevel <= 25 && waterData.value > 25) {
            const notification = await Notification.create({
              userId: device.userId,
              title: 'Low Water Level',
              message: 'Water level is below 25%. Consider refilling soon.',
              type: 'warning'
            });
            
            io.to(`device:${device._id}`).emit('notification', notification);
          } else if (newWaterLevel <= 15 && waterData.value > 15) {
            const notification = await Notification.create({
              userId: device.userId,
              title: 'Critical Water Level',
              message: 'Water level is below 15%. Please refill as soon as possible.',
              type: 'danger'
            });
            
            io.to(`device:${device._id}`).emit('notification', notification);
          }
        }
        
        // Simulate temperature fluctuation
        if (temperatureData) {
          // Random fluctuation of -0.5 to +0.5 degrees
          const fluctuation = (Math.random() - 0.5);
          const newTemperature = parseFloat((temperatureData.value + fluctuation).toFixed(1));
          
          // Create new sensor reading
          const newTempData = await SensorData.create({
            deviceId: device._id,
            type: 'temperature',
            value: newTemperature
          });
          
          // Emit update
          io.to(`device:${device._id}`).emit('temperatureUpdate', {
            temperature: newTemperature,
            timestamp: newTempData.timestamp
          });
        }
        
        // Simulate humidity fluctuation
        if (humidityData) {
          // Random fluctuation of -2 to +2 percent
          const fluctuation = Math.floor(Math.random() * 5) - 2;
          const newHumidity = Math.min(100, Math.max(0, humidityData.value + fluctuation));
          
          // Create new sensor reading
          const newHumidityData = await SensorData.create({
            deviceId: device._id,
            type: 'humidity',
            value: newHumidity
          });
          
          // Emit update
          io.to(`device:${device._id}`).emit('humidityUpdate', {
            humidity: newHumidity,
            timestamp: newHumidityData.timestamp
          });
        }
      }
    } catch (error) {
      console.error('Error simulating sensor updates:', error);
    }
  };
  
  // Run simulation every 5 minutes
  //setInterval(simulateSensorUpdates, 5 * 60 * 1000);
  
  return io;
};

module.exports = setupSocketIO;