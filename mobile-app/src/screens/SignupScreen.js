import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  Alert,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  ScrollView
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import client from '../api/client';

const SignupScreen = ({ navigation }) => {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: '',
    age: '',
    occupation: '',
    yearly_income: '',
    country: ''
  });
  const [isPasswordVisible, setIsPasswordVisible] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleChange = (key, value) => {
    setFormData(prev => ({ ...prev, [key]: value }));
  };

  const handleSignup = async () => {
    const { name, email, password, age, occupation, yearly_income, country } = formData;

    if (!name || !email || !password || !age || !occupation || !yearly_income || !country) {
      Alert.alert('Error', 'Please fill in all fields');
      return;
    }

    if (password.length < 8) {
        Alert.alert('Error', 'Password must be at least 8 characters long');
        return;
    }

    setLoading(true);
    try {
      const payload = {
        name,
        email,
        password,
        age: parseInt(age),
        occupation,
        yearly_income: parseFloat(yearly_income),
        country
      };

      await client.post('/auth/signup', payload);
      
      Alert.alert(
        'Verify Email', 
        'Account created successfully! Please verify your email address before logging in.',
        [{ text: 'OK', onPress: () => navigation.navigate('Login') }]
      );
    } catch (error) {
      console.error(error);
      const message = error.response?.data?.detail || 'Signup failed. Please try again.';
      Alert.alert('Error', message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <KeyboardAvoidingView 
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={styles.keyboardView}
      >
        <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
          <Text style={styles.title}>Create Account</Text>
          <Text style={styles.subtitle}>Join Smart Wallet today</Text>

          <View style={styles.form}>
            <View style={styles.inputContainer}>
              <Text style={styles.label}>Full Name</Text>
              <TextInput
                style={styles.input}
                placeholder="John Doe"
                placeholderTextColor="#666"
                value={formData.name}
                onChangeText={(text) => handleChange('name', text)}
              />
            </View>

            <View style={styles.inputContainer}>
              <Text style={styles.label}>Email</Text>
              <TextInput
                style={styles.input}
                placeholder="john@example.com"
                placeholderTextColor="#666"
                value={formData.email}
                onChangeText={(text) => handleChange('email', text)}
                autoCapitalize="none"
                keyboardType="email-address"
              />
            </View>

            <View style={styles.inputContainer}>
              <Text style={styles.label}>Password</Text>
              <View style={styles.passwordContainer}>
                <TextInput
                  style={styles.passwordInput}
                  placeholder="Min 8 characters"
                  placeholderTextColor="#666"
                  value={formData.password}
                  onChangeText={(text) => handleChange('password', text)}
                  secureTextEntry={!isPasswordVisible}
                />
                <TouchableOpacity 
                  onPress={() => setIsPasswordVisible(!isPasswordVisible)}
                  style={styles.eyeIcon}
                >
                  <Ionicons 
                    name={isPasswordVisible ? 'eye-off' : 'eye'} 
                    size={24} 
                    color="#666" 
                  />
                </TouchableOpacity>
              </View>
            </View>

            <View style={styles.row}>
                <View style={[styles.inputContainer, styles.halfInput]}>
                <Text style={styles.label}>Age</Text>
                <TextInput
                    style={styles.input}
                    placeholder="25"
                    placeholderTextColor="#666"
                    value={formData.age}
                    onChangeText={(text) => handleChange('age', text)}
                    keyboardType="numeric"
                />
                </View>
                <View style={[styles.inputContainer, styles.halfInput]}>
                <Text style={styles.label}>Country</Text>
                <TextInput
                    style={styles.input}
                    placeholder="USA"
                    placeholderTextColor="#666"
                    value={formData.country}
                    onChangeText={(text) => handleChange('country', text)}
                />
                </View>
            </View>

            <View style={styles.inputContainer}>
              <Text style={styles.label}>Occupation</Text>
              <TextInput
                style={styles.input}
                placeholder="Software Engineer"
                placeholderTextColor="#666"
                value={formData.occupation}
                onChangeText={(text) => handleChange('occupation', text)}
              />
            </View>

            <View style={styles.inputContainer}>
              <Text style={styles.label}>Yearly Income</Text>
              <TextInput
                style={styles.input}
                placeholder="50000"
                placeholderTextColor="#666"
                value={formData.yearly_income}
                onChangeText={(text) => handleChange('yearly_income', text)}
                keyboardType="numeric"
              />
            </View>

            <TouchableOpacity 
              style={styles.button} 
              onPress={handleSignup}
              disabled={loading}
            >
              {loading ? (
                <ActivityIndicator color="#000" />
              ) : (
                <Text style={styles.buttonText}>Sign Up</Text>
              )}
            </TouchableOpacity>

            <View style={styles.footer}>
              <Text style={styles.footerText}>Already have an account? </Text>
              <TouchableOpacity onPress={() => navigation.navigate('Login')}>
                <Text style={styles.link}>Log In</Text>
              </TouchableOpacity>
            </View>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#121212',
  },
  keyboardView: {
    flex: 1,
  },
  scrollContent: {
    padding: 24,
    paddingBottom: 40,
  },
  title: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 8,
    marginTop: 20,
    textAlign: 'center',
  },
  subtitle: {
    fontSize: 16,
    color: '#aaa',
    marginBottom: 32,
    textAlign: 'center',
  },
  form: {
    width: '100%',
  },
  inputContainer: {
    marginBottom: 20,
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  halfInput: {
    width: '48%',
  },
  label: {
    color: '#fff',
    marginBottom: 8,
    fontSize: 14,
    fontWeight: '500',
  },
  input: {
    backgroundColor: '#1E1E1E',
    borderRadius: 12,
    padding: 16,
    color: '#fff',
    fontSize: 16,
    borderWidth: 1,
    borderColor: '#333',
  },
  passwordContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#1E1E1E',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#333',
  },
  passwordInput: {
    flex: 1,
    padding: 16,
    color: '#fff',
    fontSize: 16,
  },
  eyeIcon: {
    padding: 12,
  },
  button: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
    marginTop: 16,
  },
  buttonText: {
    color: '#000',
    fontSize: 16,
    fontWeight: 'bold',
  },
  footer: {
    flexDirection: 'row',
    justifyContent: 'center',
    marginTop: 24,
    marginBottom: 20,
  },
  footerText: {
    color: '#aaa',
    fontSize: 14,
  },
  link: {
    color: '#fff',
    fontSize: 14,
    fontWeight: 'bold',
  },
});

export default SignupScreen;
