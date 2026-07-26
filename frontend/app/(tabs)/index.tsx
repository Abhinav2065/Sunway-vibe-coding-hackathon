import { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, FlatList, SafeAreaView, ScrollView, StyleSheet, Text, View } from 'react-native';
import { Image } from 'expo-image';
import * as Notifications from 'expo-notifications';

const MONKEY_API = 'http://localhost:8000/status.json';
const IMAGE_API = 'http://localhost:8000/latest.jpg';

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: true,
    shouldSetBadge: true,
  }),
});

type MonkeyStatus = {
  isMonkey: boolean;
};

type MonkeyImage = {
  id: string;
  url: string;
};

export default function MonkeyDetectionScreen() {
  const [isMonkey, setIsMonkey] = useState(false);
  const [images, setImages] = useState<MonkeyImage[]>([]);
  const [loading, setLoading] = useState(false);
  const [notificationEnabled, setNotificationEnabled] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const requestNotificationPermission = useCallback(async () => {
    const { status } = await Notifications.requestPermissionsAsync();
    setNotificationEnabled(status === 'granted');
  }, []);

  const sendMonkeyNotification = useCallback(async () => {
    await Notifications.scheduleNotificationAsync({
      content: {
        title: 'Monkey Detected',
        body: 'A monkey has been detected near your phone!',
        sound: true,
      },
      trigger: null,
    });
  }, []);

  const fetchMonkeyStatus = useCallback(async () => {
    try {
      const response = await fetch(`${MONKEY_API}/`);
      if (!response.ok) return;

      const data: MonkeyStatus = await response.json();
      const monkeyDetected = data.isMonkey === true;

      setIsMonkey(monkeyDetected);

      if (monkeyDetected) {
        await fetchMonkeyImages();
        if (notificationEnabled) {
          await sendMonkeyNotification();
        }
      }
    } catch (error) {
      console.error('Failed to fetch monkey status:', error);
    }
  }, [notificationEnabled, sendMonkeyNotification]);

  const fetchMonkeyImages = useCallback(async () => {
    if (!isMonkey) return;
    setImages([{ id: 'latest', url: `${IMAGE_API}?t=${Date.now()}` }]);
  }, [isMonkey]);

  useEffect(() => {
    requestNotificationPermission();
    fetchMonkeyStatus();
    const interval = setInterval(fetchMonkeyStatus, 5000);
    return () => clearInterval(interval);
  }, [requestNotificationPermission, fetchMonkeyStatus]);

  const renderMonkeyImage = ({ item }: { item: MonkeyImage }) => (
    <Image
      source={{ uri: item.url }}
      style={styles.monkeyImage}
      contentFit="cover"
      transition={200}
    />
  );

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scrollContent}>
        <Text style={styles.header}>Monkey Detection</Text>

        <View style={styles.statusContainer}>
          <View style={[styles.statusIndicator, isMonkey ? styles.statusActive : styles.statusInactive]} />
          <Text style={styles.statusText}>
            {isMonkey ? 'Monkey Detected!' : 'No Monkey Detected'}
          </Text>
        </View>

        {!isMonkey && (
          <View style={styles.refreshContainer}>
            <ActivityIndicator size="large" color="#007AFF" />
            <Text style={styles.refreshText}>Refreshing...</Text>
          </View>
        )}

        {isMonkey && (
          <View style={styles.imagesContainer}>
            <Text style={styles.imagesHeader}>Detected Images</Text>
            {loading ? (
              <ActivityIndicator size="large" color="#007AFF" style={styles.loader} />
            ) : (
              <FlatList
                data={images}
                renderItem={renderMonkeyImage}
                keyExtractor={(item) => item.id}
                numColumns={2}
                scrollEnabled={false}
                columnWrapperStyle={styles.row}
                ListEmptyComponent={
                  <Text style={styles.emptyText}>No monkey images available</Text>
                }
              />
            )}
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  scrollContent: {
    padding: 16,
    alignItems: 'center',
  },
  header: {
    fontSize: 28,
    fontWeight: 'bold',
    marginVertical: 20,
    color: '#1c1c1e',
  },
  statusContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    borderRadius: 12,
    backgroundColor: '#ffffff',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    elevation: 3,
    marginBottom: 20,
    width: '100%',
  },
  statusIndicator: {
    width: 16,
    height: 16,
    borderRadius: 8,
    marginRight: 12,
  },
  statusActive: {
    backgroundColor: '#34C759',
  },
  statusInactive: {
    backgroundColor: '#8E8E93',
  },
  statusText: {
    fontSize: 18,
    fontWeight: '600',
    color: '#1c1c1e',
  },
  refreshContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 40,
  },
  refreshText: {
    marginTop: 12,
    fontSize: 16,
    color: '#8E8E93',
  },
  imagesContainer: {
    width: '100%',
    marginTop: 16,
  },
  imagesHeader: {
    fontSize: 20,
    fontWeight: '600',
    marginBottom: 12,
    color: '#1c1c1e',
  },
  row: {
    justifyContent: 'space-between',
  },
  monkeyImage: {
    width: '48%',
    height: 150,
    borderRadius: 8,
    marginBottom: 12,
    backgroundColor: '#e5e5e5',
  },
  loader: {
    marginVertical: 20,
  },
  emptyText: {
    textAlign: 'center',
    color: '#8E8E93',
    marginVertical: 20,
  },
});
