// backend/services/schedulerService.js
const Schedule = require('../models/Schedule');
const Device = require('../models/Device');
const Command = require('../models/Command');
const mqttService = require('./mqttService');

// Function to check if a schedule should run based on current time and day
const shouldRunSchedule = (schedule) => {
  // Get current date and time
  const now = new Date();
  const currentDay = now.toLocaleString('en-US', { weekday: 'long' }); // 'Monday', 'Tuesday', etc.
  
  // Get current hours and minutes
  const currentHours = now.getHours();
  const currentMinutes = now.getMinutes();
  
  // Parse schedule time
  const [scheduleHours, scheduleMinutes] = schedule.time.split(':').map(Number);
  
  // Check if the schedule is set for the current day
  const isScheduledDay = schedule.days.includes(currentDay);
  
  // Check if current time matches schedule time (within a 1-minute window)
  const isScheduledTime = (
    currentHours === scheduleHours && 
    currentMinutes === scheduleMinutes
  );
  
  // Schedule should run if it's enabled, it's the right day, and it's the right time
  return schedule.enabled && isScheduledDay && isScheduledTime;
};

// Main function to check and execute schedules
const checkAndExecuteSchedules = async () => {
  try {
    console.log('🕒 Checking schedules...');
    
    // Find all enabled schedules
    const schedules = await Schedule.find({ enabled: true });
    
    if (schedules.length === 0) {
      console.log('No enabled schedules found');
      return;
    }
    
    for (const schedule of schedules) {
      if (shouldRunSchedule(schedule)) {
        console.log(`Executing schedule: ${schedule._id} (${schedule.type})`);
        
        // Check if device is valid
        const device = await Device.findById(schedule.deviceId);
        if (!device) {
          console.error(`Device not found for schedule ${schedule._id}`);
          continue;
        }
        
        // Create a command for the schedule
        const command = await Command.create({
            deviceId: schedule.deviceId,
            type: schedule.type === 'food' ? 'dispenseFood' : 'dispenseWater',
            value: schedule.amount,
            status: 'pending'
        });
        
        // Send command via MQTT
        console.log(`🚀 Sending ${schedule.type} command via MQTT for schedule ${schedule._id}`);
        const mqttSent = await mqttService.sendCommand(
            schedule.type === 'food' ? 'dispenseFood' : 'dispenseWater',
            schedule.amount,
            schedule.deviceId
        );
        
        if (mqttSent) {
            command.status = 'processing';
            await command.save();
            console.log(`✅ MQTT command sent successfully for schedule: ${schedule._id}`);
        } else {
            console.log(`❌ MQTT command failed for schedule: ${schedule._id}`);
        }
                }
            }
            } catch (error) {
            console.error('Error checking and executing schedules:', error);
            }
        };
        
        // Initialize the scheduler
        const initScheduler = () => {
            console.log('📅 Initializing scheduler service...');
            
            // Check schedules every minute
            setInterval(checkAndExecuteSchedules, 60 * 1000);
            
            // Also run immediately on startup
            checkAndExecuteSchedules();
            
            console.log('📅 Scheduler service initialized');
        };
        
        module.exports = {
            initScheduler,
            checkAndExecuteSchedules
        };