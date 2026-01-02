import React, { useState, useEffect } from 'react';
import { 
  View, 
  Text, 
  StyleSheet, 
  FlatList, 
  TextInput, 
  TouchableOpacity, 
  Alert, 
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import client from '../api/client';

const BudgetScreen = ({ navigation }) => {
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [savingId, setSavingId] = useState(null);

  const currentMonth = new Date().toLocaleDateString('en-US', { month: 'long', year: 'numeric' });

  useEffect(() => {
    fetchCategories();
  }, []);

  const fetchCategories = async () => {
    try {
      const response = await client.get('/categories/');
      // Sort categories: High budget first, then alphabetically
      const sorted = response.data.sort((a, b) => b.max_budget - a.max_budget || a.name.localeCompare(b.name));
      setCategories(sorted);
    } catch (error) {
      console.error(error);
      Alert.alert('Error', 'Failed to load categories');
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateBudget = async (id, value) => {
    const numValue = parseFloat(value);
    if (isNaN(numValue) || numValue < 0) {
        Alert.alert('Invalid Amount', 'Please enter a valid positive number');
        return;
    }

    try {
      setSavingId(id);
      await client.put(`/categories/${id}`, { max_budget: numValue });
      // Update local state
      setCategories(prev => prev.map(c => c.id === id ? { ...c, max_budget: numValue } : c));
    } catch (error) {
      console.error(error);
      Alert.alert('Error', 'Failed to update budget');
    } finally {
      setSavingId(null);
    }
  };

  const renderItem = ({ item }) => (
    <View style={styles.card}>
      <View style={styles.info}>
        <Text style={styles.categoryName}>{item.name}</Text>
        <Text style={styles.subtitle}>Monthly Limit</Text>
      </View>
      
      <View style={styles.inputWrapper}>
        <Text style={styles.currency}>₹</Text>
        <TextInput
          style={styles.input}
          keyboardType="numeric"
          defaultValue={String(item.max_budget || 0)}
          placeholder="0"
          placeholderTextColor="#666"
          returnKeyType="done"
          onSubmitEditing={(e) => handleUpdateBudget(item.id, e.nativeEvent.text)}
          onEndEditing={(e) => {
             // Only update if value changed to avoid unnecessary calls?
             // For now, let's trust onSubmitEditing or user action.
             // But onEndEditing triggers on blur too.
             handleUpdateBudget(item.id, e.nativeEvent.text);
          }}
        />
        {savingId === item.id && (
            <ActivityIndicator size="small" color="#00E676" style={styles.loader} />
        )}
      </View>
    </View>
  );

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backButton}>
          <Ionicons name="arrow-back" size={24} color="#fff" />
        </TouchableOpacity>
        <Text style={styles.title}>Monthly Budgets</Text>
        <View style={{ width: 24 }} />
      </View>

      <Text style={styles.description}>
        Set spending limits for {currentMonth}. These limits apply to the current month and recur automatically.
      </Text>

      {loading ? (
        <View style={styles.center}>
            <ActivityIndicator size="large" color="#00E676" />
        </View>
      ) : (
        <KeyboardAvoidingView 
            behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
            style={{ flex: 1 }}
        >
            <FlatList
            data={categories}
            renderItem={renderItem}
            keyExtractor={item => item.id}
            contentContainerStyle={styles.list}
            showsVerticalScrollIndicator={false}
            />
        </KeyboardAvoidingView>
      )}
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#121212',
  },
  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center'
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingVertical: 15,
    borderBottomWidth: 1,
    borderBottomColor: '#333',
  },
  backButton: {
    padding: 4,
  },
  title: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#fff',
  },
  description: {
    color: '#aaa',
    fontSize: 14,
    textAlign: 'center',
    margin: 15,
    lineHeight: 20,
  },
  list: {
    padding: 15,
    paddingBottom: 40,
  },
  card: {
    backgroundColor: '#1E1E1E',
    borderRadius: 12,
    padding: 15,
    marginBottom: 12,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    borderWidth: 1,
    borderColor: '#333',
  },
  info: {
    flex: 1,
  },
  categoryName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
    marginBottom: 4,
  },
  subtitle: {
    fontSize: 12,
    color: '#888',
  },
  inputWrapper: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#2A2A2A',
    borderRadius: 8,
    paddingHorizontal: 12,
    width: 120,
    height: 44,
  },
  currency: {
    color: '#00E676',
    fontSize: 16,
    fontWeight: 'bold',
    marginRight: 4,
  },
  input: {
    flex: 1,
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
    textAlign: 'right',
  },
  loader: {
    position: 'absolute',
    right: -24,
  }
});

export default BudgetScreen;
