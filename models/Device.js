const mongoose = require('mongoose');

const DeviceSchema = new mongoose.Schema({
  userId: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'User',
    required: true
  },
  name: {
    type: String,
    required: [true, 'Please provide a device name'],
    trim: true
  },
  serialNumber: {
    type: String,
    required: [true, 'Please provide a serial number'],
    unique: true,
    trim: true
  },
  status: {
    type: String,
    enum: ['online', 'offline', 'maintenance'],
    default: 'offline'
  },
  lastConnected: {
    type: Date,
    default: Date.now
  }
}, {
  timestamps: true
});

module.exports = mongoose.model('Device', DeviceSchema);