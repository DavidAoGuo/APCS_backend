const express = require('express');
const router = express.Router();
const { 
  getAllSensorData, 
  getSensorHistory,
  addSensorReading
} = require('../controllers/sensorController');
const { protect } = require('../middleware/authMiddleware');

// All routes are protected
router.use(protect);

router.get('/', getAllSensorData);
router.get('/history', getSensorHistory);
router.post('/:type', addSensorReading);

module.exports = router;