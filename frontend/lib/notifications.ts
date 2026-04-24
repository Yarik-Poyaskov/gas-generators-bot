import api from './api';

export async function registerServiceWorker() {
  if ('serviceWorker' in navigator) {
    try {
      const registration = await navigator.serviceWorker.register('/sw.js');
      console.log('Service Worker registered with scope:', registration.scope);
      return registration;
    } catch (error) {
      console.error('Service Worker registration failed:', error);
    }
  }
}

export async function subscribeToNotifications() {
  try {
    const registration = await navigator.serviceWorker.ready;
    
    // Get public key from server
    const { data } = await api.get('/notifications/vapid-public-key');
    const publicKey = data.public_key;

    const subscription = await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: publicKey
    });

    // Send subscription to server
    await api.post('/notifications/subscribe', subscription);
    console.log('User is subscribed to Push Notifications');
    return true;
  } catch (error) {
    console.error('Failed to subscribe user:', error);
    return false;
  }
}

export async function checkSubscriptionStatus() {
  if ('serviceWorker' in navigator) {
    const registration = await navigator.serviceWorker.ready;
    const subscription = await registration.pushManager.getSubscription();
    return !!subscription;
  }
  return false;
}
