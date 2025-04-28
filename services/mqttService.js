const mqtt = require('mqtt');
const SensorData = require('../models/SensorData');
const Command = require('../models/Command');
const Device = require('../models/Device');
const Notification = require('../models/Notification');

class MqttService {
  constructor() {
    this.client = null;
    this.connected = false;
    // Use the same broker as the hardware team is using now
    this.brokerUrl = 'mqtt://broker.hivemq.com:1883';
    this.c2sTopic = '/seniorDesign/c2s'; // Client to server (hardware to our backend)
    this.s2cTopic = '/seniorDesign/s2c'; // Server to client (our backend to hardware)
  }

  initialize() {
    console.log('Initializing MQTT service...');
    console.log(`Connecting to broker: ${this.brokerUrl}`);
    console.log(`Topics - c2s: ${this.c2sTopic} s2c: ${this.s2cTopic}`);
    
    this.client = mqtt.connect(this.brokerUrl, {
      clientId: 'apcs_backend_' + Math.random().toString(16).substring(2, 8),
      clean: true,
      reconnectPeriod: 1000
    });
    
    this.client.on('connect', () => {
      console.log(`✅ Connected to MQTT broker: ${this.brokerUrl}`);
      this.connected = true;
      
      // First clear any retained messages
      this.clearRetainedMessages();
      
      // Subscribe to topic for receiving sensor data
      this.client.subscribe(this.c2sTopic, { qos: 1 }, (err) => {
        if (err) {
          console.error(`❌ Failed to subscribe to ${this.c2sTopic}:`, err);
        } else {
          console.log(`✅ Subscribed to ${this.c2sTopic}`);
          
          // Send a test message to s2c to verify our command channel (with retain=false)
          this.client.publish(this.s2cTopic, 'TEST-COMMAND-INIT', { qos: 1, retain: false }, (err) => {
            if (err) {
              console.error('❌ Test command failed:', err);
            } else {
              console.log(`✅ Test command published to ${this.s2cTopic}`);
            }
          });
        }
      });
    });
    
    this.client.on('message', (topic, message) => {
      const messageStr = message.toString();
      console.log(`📥 Received message on ${topic}: "${messageStr}"`);
      
      if (topic === this.c2sTopic) {
        this.handleSensorData(messageStr);
      }
    });
    
    this.client.on('error', (error) => {
      console.error(`❌ MQTT error: ${error.message}`);
      this.connected = false;
    });
    
    this.client.on('offline', () => {
      console.warn('⚠️ MQTT client went offline');
      this.connected = false;
    });
    
    this.client.on('reconnect', () => {
      console.log('🔄 Attempting to reconnect to MQTT broker...');
    });
  }

  clearRetainedMessages() {
    console.log('Clearing any retained messages on topics...');
    // Send empty message with retain flag to clear retained messages
    this.client.publish(this.s2cTopic, '', { qos: 1, retain: true }, (err) => {
      if (!err) {
        console.log(`✅ Cleared retained messages on ${this.s2cTopic}`);
      } else {
        console.error(`❌ Failed to clear retained messages: ${err}`);
      }
    });
  }

  async handleSensorData(data) {
    try {
      console.log('🔍 MQTT MESSAGE RECEIVED - Raw data:', data);
      
      // Skip test messages
      if (data.startsWith('TEST-')) {
        console.log('This is a test message, skipping processing');
        return;
      }
      
      // Parse the comma-separated values
      const values = data.split(',').map(val => parseFloat(val.trim()));
      
      if (values.length < 4 || values.some(isNaN)) {
        console.error('❌ Invalid sensor data format:', data);
        return;
      }
      
      console.log('📊 PARSED VALUES:', JSON.stringify({
        foodLevel: values[0],
        waterLevel: values[1],
        temperature: values[2],
        humidity: values[3]
      }));
      
      // Get all active devices
      const devices = await Device.find({ status: 'online' });
      
      if (devices.length === 0) {
        console.warn('⚠️ No active devices found to update with sensor data');
        return;
      }
      
      console.log(`✅ Found ${devices.length} active devices to update`);
      
      // Process each device
      let updatedDevice = null;
      for (const device of devices) {
        console.log(`📱 Updating device: ${device._id} (${device.name})`);
        updatedDevice = device;
        
        // Map values to sensor types
        const sensorData = [
          { type: 'food', value: values[0] },
          { type: 'water', value: values[1] },
          { type: 'temperature', value: values[2] },
          { type: 'humidity', value: values[3] }
        ];
        
        // Save all sensor readings to the database
        const newReadings = [];
        for (const sensor of sensorData) {
          const newReading = await SensorData.create({
            deviceId: device._id,
            type: sensor.type,
            value: sensor.value
          });
          
          newReadings.push(newReading);
          console.log(`✅ Created new ${sensor.type} reading: ${newReading._id} with value ${sensor.value}`);
          
          // Check thresholds and create notifications if needed
          if (sensor.type === 'food') {
            if (sensor.value <= 10) {
              const notification = await this.createNotificationForSensorThreshold(
                device._id, 'food', sensor.value, 10, 'critical'
              );
              if (notification) {
                // Try to emit notification via Socket.IO
                try {
                  const io = require('socket.io').instance;
                  if (io) {
                    io.to(`device:${device._id}`).emit('notification', notification);
                  }
                } catch (error) {
                  console.error('❌ Error emitting notification via Socket.IO:', error);
                }
              }
            } else if (sensor.value <= 20) {
              const notification = await this.createNotificationForSensorThreshold(
                device._id, 'food', sensor.value, 20, 'warning'
              );
              if (notification) {
                // Try to emit notification via Socket.IO
                try {
                  const io = require('socket.io').instance;
                  if (io) {
                    io.to(`device:${device._id}`).emit('notification', notification);
                  }
                } catch (error) {
                  console.error('❌ Error emitting notification via Socket.IO:', error);
                }
              }
            }
          } else if (sensor.type === 'water') {
            if (sensor.value <= 15) {
              const notification = await this.createNotificationForSensorThreshold(
                device._id, 'water', sensor.value, 15, 'critical'
              );
              if (notification) {
                // Try to emit notification via Socket.IO
                try {
                  const io = require('socket.io').instance;
                  if (io) {
                    io.to(`device:${device._id}`).emit('notification', notification);
                  }
                } catch (error) {
                  console.error('❌ Error emitting notification via Socket.IO:', error);
                }
              }
            } else if (sensor.value <= 25) {
              const notification = await this.createNotificationForSensorThreshold(
                device._id, 'water', sensor.value, 25, 'warning'
              );
              if (notification) {
                // Try to emit notification via Socket.IO
                try {
                  const io = require('socket.io').instance;
                  if (io) {
                    io.to(`device:${device._id}`).emit('notification', notification);
                  }
                } catch (error) {
                  console.error('❌ Error emitting notification via Socket.IO:', error);
                }
              }
            }
          }
          // Add temperature and humidity checks if needed
        }
        
        // Log complete sensor update summary
        console.log('📊 SENSORS UPDATED:', JSON.stringify({
          deviceId: device._id,
          deviceName: device.name,
          timestamp: new Date().toISOString(),
          readings: sensorData.map(s => ({ type: s.type, value: s.value }))
        }));
      }
      
      return { success: true, device: updatedDevice };
    } catch (error) {
      console.error('❌ Error processing sensor data:', error);
      return { success: false, error: error.message };
    }
  }

  async createNotificationForSensorThreshold(deviceId, type, value, threshold, level) {
    try {
      // Get the device to find the user
      const device = await Device.findById(deviceId);
      if (!device) {
        console.error(`❌ Device not found for notification: ${deviceId}`);
        return null;
      }
  
      let title, message, notificationType;
      
      switch (type) {
        case 'food':
          title = level === 'warning' ? 'Low Food Level' : 'Critical Food Level';
          message = level === 'warning' 
            ? `Food level is at ${value}%. Consider refilling soon.` 
            : `Food level is critically low at ${value}%. Please refill as soon as possible.`;
          notificationType = level === 'warning' ? 'warning' : 'danger';
          break;
        case 'water':
          title = level === 'warning' ? 'Low Water Level' : 'Critical Water Level';
          message = level === 'warning' 
            ? `Water level is at ${value}%. Consider refilling soon.` 
            : `Water level is critically low at ${value}%. Please refill as soon as possible.`;
          notificationType = level === 'warning' ? 'warning' : 'danger';
          break;
        case 'temperature':
          title = 'Temperature Alert';
          message = `Temperature is ${value > threshold ? 'above' : 'below'} the recommended range at ${value}°C.`;
          notificationType = 'warning';
          break;
        case 'humidity':
          title = 'Humidity Alert';
          message = `Humidity is ${value > threshold ? 'above' : 'below'} the recommended range at ${value}%.`;
          notificationType = 'warning';
          break;
        default:
          return null;
      }
      
      // Create notification
      const notification = await Notification.create({
        userId: device.userId,
        title,
        message,
        type: notificationType,
        read: false
      });
      
      console.log(`✅ Created notification: ${notification._id}`);
      return notification;
    } catch (error) {
      console.error('❌ Error creating notification:', error);
      return null;
    }
  }

  async sendCommand(commandType, value, deviceId) {
    if (!this.connected || !this.client) {
      console.error('❌ MQTT client not connected, cannot send command');
      return false;
    }
    
    try {
      let mqttCommand = '';
      
      // Map command types to hardware-specific command strings
      switch (commandType) {
        case 'dispenseFood':
          mqttCommand = `F${value}`; // Food refill command
          break;
        case 'dispenseWater':
          mqttCommand = `W${value}`; // Water refill command
          break;
        case 'setTemperature':
          mqttCommand = `T${value}`; // Temperature command
          break;
        default:
          console.error('❌ Unknown command type:', commandType);
          return false;
      }
      
      console.log(`🚀 SENDING COMMAND TO HARDWARE: ${mqttCommand} for ${commandType} (value: ${value})`);
      
      // Create a command record in the database
      const command = await Command.create({
        deviceId,
        type: commandType,
        value: value || 0,
        status: 'pending'
      });
      
      console.log(`✅ Command record created: ${command._id}`);
      
      // Use a simpler, more explicit method to publish
      return new Promise((resolve) => {
        // Debug info
        console.log(`Publishing to topic: ${this.s2cTopic}`);
        console.log(`Message content: ${mqttCommand}`);
        
        // Send the actual command with explicit options
        this.client.publish(this.s2cTopic, mqttCommand, { 
          qos: 1, 
          retain: false
        }, (err) => {
          if (err) {
            console.error('❌ Failed to publish command:', err);
            resolve(false);
            return;
          }
          
          console.log(`✅ MQTT COMMAND PUBLISHED: "${mqttCommand}" to topic: ${this.s2cTopic}`);
          
          // Update command status to sent
          Command.findByIdAndUpdate(command._id, { status: 'processing' })
            .then(() => {
              console.log(`✅ Command status updated to processing: ${command._id}`);
              resolve(true);
            })
            .catch(err => {
              console.error('❌ Error updating command status:', err);
              resolve(false);
            });
        });
      });
    } catch (error) {
      console.error('❌ Error sending command:', error);
      return false;
    }
  }
  
  // Manual test function
  testConnection() {
    if (!this.connected || !this.client) {
      console.log('❌ Cannot test - MQTT client not connected');
      return;
    }
    
    console.log('🧪 Running MQTT connection test...');
    
    // Test command publishing
    this.client.publish(this.s2cTopic, 'TEST-COMMAND-MANUAL', { qos: 1, retain: false }, (err) => {
      if (err) {
        console.error('❌ Test command failed:', err);
      } else {
        console.log(`✅ Manual test command published to ${this.s2cTopic}`);
      }
    });
  }
  
  // New direct test method
  async directTest() {
    console.log('🛠️ Running direct MQTT test...');
    
    try {
      // Create a completely new client
      const mqtt = require('mqtt');
      const testClient = mqtt.connect(this.brokerUrl, {
        clientId: 'direct_test_' + Math.random().toString(16).substring(2, 8),
        clean: true
      });
      
      return new Promise((resolve) => {
        testClient.on('connect', () => {
          console.log('🛠️ Direct test client connected');
          
          testClient.publish(this.s2cTopic, 'DIRECT-TEST-MESSAGE', { qos: 1, retain: false }, (err) => {
            if (err) {
              console.error('🛠️ Direct test publish failed:', err);
              resolve(false);
            } else {
              console.log('🛠️ Direct test message published successfully');
              resolve(true);
            }
            
            setTimeout(() => {
              testClient.end();
              console.log('🛠️ Direct test client disconnected');
            }, 1000);
          });
        });
        
        testClient.on('error', (err) => {
          console.error('🛠️ Direct test client error:', err);
          resolve(false);
        });
        
        // Timeout after 5 seconds
        setTimeout(() => {
          console.log('🛠️ Direct test timed out');
          resolve(false);
        }, 5000);
      });
    } catch (error) {
      console.error('🛠️ Error in direct test:', error);
      return false;
    }
  }
}

// Create a singleton instance
const mqttService = new MqttService();

module.exports = mqttService;