import React, { useState } from 'react';
import { 
  View, 
  Text, 
  TouchableOpacity, 
  StyleSheet, 
  Modal, 
  Alert,
  ActivityIndicator,
  ScrollView
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import * as DocumentPicker from 'expo-document-picker';
import { Ionicons } from '@expo/vector-icons';
import client from '../api/client';

const STATEMENT_TYPES = ['Bank', 'Credit Card', 'UPI'];

const HomeScreen = () => {
  const [statementType, setStatementType] = useState(STATEMENT_TYPES[0]);
  const [modalVisible, setModalVisible] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [file, setFile] = useState(null);
  const [processing, setProcessing] = useState(false);
  const [jobStatus, setJobStatus] = useState(null);
  const [statusMessage, setStatusMessage] = useState('');

  const pollJobStatus = async (jobId) => {
    try {
      const response = await client.get(`/ai/job-status/${jobId}`);
      const { status, result, error } = response.data;
      
      setJobStatus(status);
      
      if (status === 'done') {
        setProcessing(false);
        setStatusMessage('Magic complete! Your insights are ready.');
        Alert.alert('Success', 'AI Agent finished processing your transactions!');
      } else if (status === 'error') {
        setProcessing(false);
        setStatusMessage(`Error: ${error}`);
        Alert.alert('Error', `Job failed: ${error}`);
      } else {
        setStatusMessage(`Status: ${status}... (checking again in 15s)`);
        // Poll again in 15 seconds
        setTimeout(() => pollJobStatus(jobId), 15000);
      }
    } catch (error) {
      console.error('Polling error:', error);
      setProcessing(false);
      setStatusMessage('Error checking status');
    }
  };

  const startMagic = async () => {
    try {
      setProcessing(true);
      setJobStatus('starting');
      setStatusMessage('Starting AI Agent...');
      
      const response = await client.post('/ai/run-agent-async');
      const { job_id } = response.data;
      
      console.log('Job started:', job_id);
      setStatusMessage('AI Agent is running...');
      
      // Start polling
      setTimeout(() => pollJobStatus(job_id), 15000);
      
    } catch (error) {
      console.error('Start magic error:', error);
      setProcessing(false);
      Alert.alert('Error', 'Failed to start AI Agent');
    }
  };

  const pickDocument = async () => {
    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: 'application/pdf',
        copyToCacheDirectory: true,
      });

      if (result.canceled === false) {
        setFile(result.assets[0]);
      }
    } catch (err) {
      console.log('Document Picker Error:', err);
      Alert.alert('Error', 'Failed to pick document');
    }
  };

  const handleUpload = async () => {
    if (!file) {
      Alert.alert('Error', 'Please select a file first');
      return;
    }

    setUploading(true);
    const formData = new FormData();
    
    formData.append('file', {
      uri: file.uri,
      name: file.name,
      type: 'application/pdf',
    });
    formData.append('statement_type', statementType);

    try {
      // Note: user_id is handled by the backend via JWT token
      await client.post('/upload-statement/', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      
      Alert.alert('Success', 'Statement uploaded successfully for processing!');
      setFile(null);
    } catch (error) {
      console.error('Upload error:', error);
      Alert.alert('Error', 'Failed to upload statement. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView style={styles.content}>
        <Text style={styles.title}>Smart Wallet</Text>
        <Text style={styles.description}>
          Upload your financial statements to get AI-powered insights and track your spending habits.
        </Text>

        <View style={styles.card}>
            <Text style={styles.label}>Select Statement Type</Text>
            <TouchableOpacity 
                style={styles.dropdown}
                onPress={() => setModalVisible(true)}
            >
                <Text style={styles.dropdownText}>{statementType}</Text>
                <Ionicons name="chevron-down" size={20} color="#fff" />
            </TouchableOpacity>

            <TouchableOpacity style={styles.fileButton} onPress={pickDocument}>
                <Ionicons name={file ? "document" : "cloud-upload"} size={32} color="#000" />
                <Text style={styles.fileButtonText}>
                    {file ? file.name : "Select PDF Statement"}
                </Text>
            </TouchableOpacity>

            {file && (
                <TouchableOpacity 
                    style={styles.uploadButton} 
                    onPress={handleUpload}
                    disabled={uploading}
                >
                    {uploading ? (
                        <ActivityIndicator color="#fff" />
                    ) : (
                        <Text style={styles.uploadButtonText}>Upload Statement</Text>
                    )}
                </TouchableOpacity>
            )}
        </View>

        <View style={[styles.card, { marginTop: 24, marginBottom: 40 }]}>
            <Text style={styles.label}>AI Processing</Text>
            <Text style={[styles.description, { marginBottom: 20 }]}>
                Run the AI Agent to process your uploaded statements and generate insights.
            </Text>
            <TouchableOpacity 
                style={[styles.uploadButton, { backgroundColor: '#9C27B0' }]} 
                onPress={startMagic}
                disabled={processing}
            >
                {processing ? (
                    <ActivityIndicator color="#fff" />
                ) : (
                    <Text style={styles.uploadButtonText}>Start Magic 🪄</Text>
                )}
            </TouchableOpacity>
            
            {statusMessage ? (
                <Text style={[styles.description, { marginTop: 16, marginBottom: 0, textAlign: 'center', color: '#fff' }]}>
                    {statusMessage}
                </Text>
            ) : null}
        </View>

        <Modal
            animationType="slide"
            transparent={true}
            visible={modalVisible}
            onRequestClose={() => setModalVisible(false)}
        >
            <View style={styles.modalOverlay}>
                <View style={styles.modalContent}>
                    <Text style={styles.modalTitle}>Select Type</Text>
                    {STATEMENT_TYPES.map((type) => (
                        <TouchableOpacity
                            key={type}
                            style={styles.modalItem}
                            onPress={() => {
                                setStatementType(type);
                                setModalVisible(false);
                            }}
                        >
                            <Text style={[
                                styles.modalItemText, 
                                statementType === type && styles.selectedItemText
                            ]}>
                                {type}
                            </Text>
                            {statementType === type && (
                                <Ionicons name="checkmark" size={20} color="#4A90E2" />
                            )}
                        </TouchableOpacity>
                    ))}
                    <TouchableOpacity 
                        style={styles.closeButton}
                        onPress={() => setModalVisible(false)}
                    >
                        <Text style={styles.closeButtonText}>Cancel</Text>
                    </TouchableOpacity>
                </View>
            </View>
        </Modal>
      </ScrollView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#121212',
  },
  content: {
    flex: 1,
    padding: 24,
  },
  title: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 16,
  },
  description: {
    fontSize: 16,
    color: '#aaa',
    marginBottom: 40,
    lineHeight: 24,
  },
  card: {
    backgroundColor: '#1E1E1E',
    borderRadius: 16,
    padding: 24,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#333',
  },
  label: {
    color: '#aaa',
    alignSelf: 'flex-start',
    marginBottom: 8,
    fontSize: 14,
  },
  dropdown: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: '#2C2C2C',
    padding: 16,
    borderRadius: 12,
    width: '100%',
    marginBottom: 24,
  },
  dropdownText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '500',
  },
  fileButton: {
    width: 140,
    height: 140,
    borderRadius: 70,
    backgroundColor: '#fff',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 24,
    padding: 16,
  },
  fileButtonText: {
    color: '#000',
    marginTop: 8,
    textAlign: 'center',
    fontSize: 12,
    fontWeight: '500',
  },
  uploadButton: {
    backgroundColor: '#4A90E2',
    paddingVertical: 16,
    paddingHorizontal: 32,
    borderRadius: 30,
    width: '100%',
    alignItems: 'center',
  },
  uploadButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: '#1E1E1E',
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    padding: 24,
  },
  modalTitle: {
    color: '#fff',
    fontSize: 20,
    fontWeight: 'bold',
    marginBottom: 16,
    textAlign: 'center',
  },
  modalItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#333',
  },
  modalItemText: {
    color: '#fff',
    fontSize: 16,
  },
  selectedItemText: {
    color: '#4A90E2',
    fontWeight: 'bold',
  },
  closeButton: {
    marginTop: 16,
    paddingVertical: 16,
    alignItems: 'center',
  },
  closeButtonText: {
    color: '#FF4444',
    fontSize: 16,
    fontWeight: '500',
  },
});

export default HomeScreen;
