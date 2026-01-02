import React, { useState, useEffect } from 'react';
import { 
  View, 
  Text, 
  StyleSheet, 
  TouchableOpacity, 
  ScrollView, 
  ActivityIndicator, 
  Alert 
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import Markdown from 'react-native-markdown-display';
import client, { setAuthToken } from '../api/client';

const getScoreColor = (score, isHighGood) => {
  if (score === null || score === undefined) return '#fff';
  if (isHighGood) {
    if (score >= 80) return '#00C853'; // Green
    if (score >= 50) return '#FFD600'; // Yellow
    return '#FF4444'; // Red
  } else {
    if (score <= 20) return '#00C853'; // Green
    if (score <= 50) return '#FFD600'; // Yellow
    return '#FF4444'; // Red
  }
};

const ProfileScreen = ({ navigation }) => {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [insights, setInsights] = useState(null);
  const [statusMessage, setStatusMessage] = useState('');

  useEffect(() => {
    fetchProfile();
    fetchLatestInsights();
  }, []);

  const fetchProfile = async () => {
    try {
      const response = await client.get('/auth/profile');
      setProfile(response.data);
    } catch (error) {
      console.error('Fetch profile error:', error);
      Alert.alert('Error', 'Failed to load profile');
    } finally {
      setLoading(false);
    }
  };

  const fetchLatestInsights = async () => {
    try {
      const response = await client.get('/ai/insights');
      if (response.data && response.data.insights) {
        setInsights(response.data.insights.content);
      }
    } catch (error) {
      console.log('Fetch insights error:', error);
      // Don't alert here, just silently fail if no insights
    }
  };

  const handleLogout = async () => {
    await setAuthToken(null);
    navigation.replace('Login');
  };

  const pollJobStatus = async (jobId) => {
    try {
      const response = await client.get(`/ai/job-status/${jobId}`);
      const { status, result, error } = response.data;
      
      if (status === 'done') {
        setProcessing(false);
        // The result structure depends on how run_insights_job returns data
        // Assuming result contains the insights text
        if (result && result.insights) {
             setInsights(result.insights);
        } else {
             setInsights(JSON.stringify(result, null, 2));
        }
        setStatusMessage('Insights generated successfully!');
        fetchLatestInsights(); // Refresh from DB to be sure
      } else if (status === 'error') {
        setProcessing(false);
        setStatusMessage(`Error: ${error}`);
        Alert.alert('Error', `Generation failed: ${error}`);
      } else {
        setStatusMessage('Generating financial insights...');
        // Poll again in 5 seconds
        setTimeout(() => pollJobStatus(jobId), 5000);
      }
    } catch (error) {
      console.error('Polling error:', error);
      setProcessing(false);
      setStatusMessage('Error checking status');
    }
  };

  const generateInsights = async () => {
    try {
      setProcessing(true);
      setInsights(null);
      setStatusMessage('Starting analysis...');
      
      const response = await client.post('/ai/generate-insights');
      const { job_id } = response.data;
      
      console.log('Insights job started:', job_id);
      
      // Start polling
      setTimeout(() => pollJobStatus(job_id), 2000);
      
    } catch (error) {
      console.error('Generate insights error:', error);
      setProcessing(false);
      Alert.alert('Error', 'Failed to start insight generation');
    }
  };

  if (loading) {
    return (
      <SafeAreaView style={styles.container}>
        <ActivityIndicator size="large" color="#4A90E2" style={styles.loader} />
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Profile</Text>
        <TouchableOpacity onPress={handleLogout} style={styles.logoutButton}>
          <Ionicons name="log-out-outline" size={24} color="#FF4444" />
        </TouchableOpacity>
      </View>

      <ScrollView style={styles.content}>
        {profile && (
          <View style={styles.card}>
            <View style={styles.avatarContainer}>
              <View style={styles.avatar}>
                <Text style={styles.avatarText}>
                  {profile.name ? profile.name.charAt(0).toUpperCase() : 'U'}
                </Text>
              </View>
              <Text style={styles.name}>{profile.name}</Text>
              <Text style={styles.email}>{profile.email}</Text>
            </View>

            <View style={styles.divider} />

            <View style={styles.detailsRow}>
              <View style={styles.detailItem}>
                <Text style={styles.detailLabel}>Age</Text>
                <Text style={styles.detailValue}>{profile.age}</Text>
              </View>
              <View style={styles.detailItem}>
                <Text style={styles.detailLabel}>Country</Text>
                <Text style={styles.detailValue}>{profile.country}</Text>
              </View>
            </View>

            <View style={styles.detailsRow}>
              <View style={styles.detailItem}>
                <Text style={styles.detailLabel}>Occupation</Text>
                <Text style={styles.detailValue}>{profile.occupation}</Text>
              </View>
            </View>

            <View style={styles.detailsRow}>
              <View style={styles.detailItem}>
                <Text style={styles.detailLabel}>Yearly Income</Text>
                <Text style={styles.detailValue}>₹{profile.yearly_income?.toLocaleString()}</Text>
              </View>
            </View>

            <View style={styles.divider} />

            <View style={styles.detailsRow}>
              <View style={styles.detailItem}>
                <Text style={styles.detailLabel}>Budget Adherence</Text>
                <Text style={[styles.detailValue, { color: getScoreColor(profile.budget_adherence_score, true) }]}>
                  {profile.budget_adherence_score !== null && profile.budget_adherence_score !== undefined 
                    ? `${profile.budget_adherence_score}%` 
                    : 'N/A'}
                </Text>
              </View>
              <View style={styles.detailItem}>
                <Text style={styles.detailLabel}>Impulse Buy Score</Text>
                <Text style={[styles.detailValue, { color: getScoreColor(profile.impulse_buy_score, false) }]}>
                  {profile.impulse_buy_score !== null && profile.impulse_buy_score !== undefined 
                    ? `${profile.impulse_buy_score}%` 
                    : 'N/A'}
                </Text>
              </View>
            </View>
          </View>
        )}

        <View style={styles.actionSection}>
          <TouchableOpacity 
            style={[styles.generateButton, { backgroundColor: '#2A2A2A', marginBottom: 12, flexDirection: 'row', justifyContent: 'center' }]}
            onPress={() => navigation.navigate('Budget')}
          >
            <Ionicons name="wallet-outline" size={20} color="#fff" style={{ marginRight: 8 }} />
            <Text style={styles.generateButtonText}>Manage Monthly Budgets</Text>
          </TouchableOpacity>

          <TouchableOpacity 
            style={styles.generateButton}
            onPress={generateInsights}
            disabled={processing}
          >
            {processing ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.generateButtonText}>Generate Financial Insights</Text>
            )}
          </TouchableOpacity>
          {statusMessage ? <Text style={styles.statusText}>{statusMessage}</Text> : null}
        </View>

        {insights && (
          <View style={styles.insightsContainer}>
            <Text style={styles.insightsTitle}>Financial Report</Text>
            <View style={styles.markdownBox}>
                <Markdown style={markdownStyles}>
                    {insights}
                </Markdown>
            </View>
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#121212',
  },
  loader: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 24,
    paddingVertical: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#333',
  },
  headerTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#fff',
  },
  logoutButton: {
    padding: 8,
  },
  content: {
    flex: 1,
    padding: 24,
  },
  card: {
    backgroundColor: '#1E1E1E',
    borderRadius: 16,
    padding: 24,
    marginBottom: 24,
  },
  avatarContainer: {
    alignItems: 'center',
    marginBottom: 24,
  },
  avatar: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: '#4A90E2',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 16,
  },
  avatarText: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#fff',
  },
  name: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 4,
  },
  email: {
    fontSize: 14,
    color: '#aaa',
  },
  divider: {
    height: 1,
    backgroundColor: '#333',
    marginVertical: 16,
  },
  detailsRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 16,
  },
  detailItem: {
    flex: 1,
  },
  detailLabel: {
    fontSize: 12,
    color: '#aaa',
    marginBottom: 4,
  },
  detailValue: {
    fontSize: 16,
    color: '#fff',
    fontWeight: '500',
  },
  actionSection: {
    marginBottom: 24,
    alignItems: 'center',
  },
  generateButton: {
    backgroundColor: '#00C853',
    paddingVertical: 16,
    paddingHorizontal: 32,
    borderRadius: 30,
    width: '100%',
    alignItems: 'center',
  },
  generateButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
  },
  statusText: {
    color: '#aaa',
    marginTop: 12,
    fontSize: 14,
  },
  insightsContainer: {
    backgroundColor: '#1E1E1E',
    borderRadius: 16,
    padding: 24,
    marginBottom: 40,
  },
  insightsTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#333',
    paddingBottom: 8,
  },
  markdownBox: {
    width: '100%',
  }
});

const markdownStyles = StyleSheet.create({
  body: {
    color: '#ddd',
    fontSize: 14,
    lineHeight: 22,
  },
  heading1: {
    color: '#fff',
    fontSize: 22,
    fontWeight: 'bold',
    marginTop: 16,
    marginBottom: 8,
  },
  heading2: {
    color: '#fff',
    fontSize: 18,
    fontWeight: 'bold',
    marginTop: 12,
    marginBottom: 8,
  },
  heading3: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
    marginTop: 8,
    marginBottom: 4,
  },
  list_item: {
    color: '#ddd',
    marginVertical: 4,
  },
  strong: {
    color: '#fff',
    fontWeight: 'bold',
  },
});

export default ProfileScreen;
