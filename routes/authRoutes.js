const express = require('express');
const router = express.Router();
const { 
  register, 
  login, 
  refreshToken, 
  getUserProfile,
  verifyAuth,
  logout,
  updateProfile,
  changePassword
} = require('../controllers/authController');
const { protect } = require('../middleware/authMiddleware');

// Public routes
router.post('/register', register);
router.post('/login', login);
router.post('/refresh-token', refreshToken);

// Protected routes
router.get('/profile', protect, getUserProfile);
router.put('/profile', protect, updateProfile); 
router.put('/change-password', protect, changePassword); 
router.get('/verify', protect, verifyAuth);
router.post('/logout', protect, logout);


module.exports = router;