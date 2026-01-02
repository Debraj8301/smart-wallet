import React, { useState, useEffect, useCallback } from 'react';
import { 
  View, 
  Text, 
  StyleSheet, 
  TouchableOpacity, 
  ActivityIndicator,
  Alert,
  Dimensions,
  ScrollView,
  RefreshControl
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { PieChart } from 'react-native-chart-kit';
import client from '../api/client';
import { useFocusEffect } from '@react-navigation/native';

const SCREEN_WIDTH = Dimensions.get('window').width;

const CHART_CONFIG = {
  backgroundGradientFrom: "#1E1E1E",
  backgroundGradientTo: "#1E1E1E",
  color: (opacity = 1) => `rgba(255, 255, 255, ${opacity})`,
  strokeWidth: 2,
  barPercentage: 0.7,
  useShadowColorFromDataset: false,
  decimalPlaces: 0,
};

const InsightsScreen = () => {
  // Insights State
  const [stats, setStats] = useState(null);
  const [statsLoading, setStatsLoading] = useState(false);
  const [selectedMonth, setSelectedMonth] = useState(new Date());

  useFocusEffect(
    useCallback(() => {
      fetchStats();
    }, [selectedMonth])
  );

  // --- Insights Functions ---
  const fetchStats = async () => {
    setStatsLoading(true);
    try {
      const monthStr = selectedMonth.toISOString().slice(0, 7); // YYYY-MM
      const response = await client.get(`/transactions/stats?month=${monthStr}`);
      setStats(response.data);
    } catch (error) {
      console.error('Fetch stats error:', error);
      Alert.alert('Error', 'Failed to load insights');
    } finally {
      setStatsLoading(false);
    }
  };

  const changeMonth = (delta) => {
    const newDate = new Date(selectedMonth);
    newDate.setMonth(newDate.getMonth() + delta);
    setSelectedMonth(newDate);
  };

  // --- Render Functions ---

  const renderInsights = () => {
    const monthLabel = selectedMonth.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });

    if (statsLoading) {
      return <ActivityIndicator size="large" color="#4A90E2" style={{ marginTop: 50 }} />;
    }

    if (!stats || !stats.charts) {
      return <Text style={styles.emptyText}>No data available for this month.</Text>;
    }

    // Prepare Data for Charts
    
    // 1. Pie Chart: Category Debits
    const categoryData = Object.entries(stats.charts.category_debits || {})
      .map(([name, amount], index) => ({
        name,
        amount,
        color: getRandomColor(index),
        legendFontColor: "#ccc",
        legendFontSize: 12
      }))
      .sort((a, b) => b.amount - a.amount); // Sort largest first

    // 2. Behavioral Tags (Custom Horizontal Bar)
    const tagEntries = Object.entries(stats.charts.tag_spending || {})
       .filter(([_, val]) => val > 0) // Only show non-zero tags
       .sort((a, b) => b[1] - a[1]);
    
    // 3. Payment Type Distribution (Pie)
    const paymentData = Object.entries(stats.charts.payment_type_distribution || {})
      .map(([name, amount], index) => ({
        name,
        amount,
        color: getRandomColor(index + 5), // Offset colors
        legendFontColor: "#ccc",
        legendFontSize: 12
      }));

    return (
      <ScrollView 
        contentContainerStyle={styles.scrollContent}
        refreshControl={
          <RefreshControl refreshing={statsLoading} onRefresh={fetchStats} tintColor="#fff" />
        }
      >
        {/* Month Picker */}
        <View style={styles.monthPicker}>
          <TouchableOpacity onPress={() => changeMonth(-1)} style={styles.arrowBtn}>
            <Ionicons name="chevron-back" size={24} color="#fff" />
          </TouchableOpacity>
          <Text style={styles.monthLabel}>{monthLabel}</Text>
          <TouchableOpacity onPress={() => changeMonth(1)} style={styles.arrowBtn}>
            <Ionicons name="chevron-forward" size={24} color="#fff" />
          </TouchableOpacity>
        </View>

        {/* 1. Category Pie Chart */}
        <View style={styles.chartContainer}>
          <Text style={styles.chartTitle}>Category Spending (Debit)</Text>
          {categoryData.length > 0 ? (
            <View>
              <PieChart
                data={categoryData}
                width={SCREEN_WIDTH - 32}
                height={220}
                chartConfig={CHART_CONFIG}
                accessor={"amount"}
                backgroundColor={"transparent"}
                paddingLeft={"15"}
                center={[10, 0]}
                hasLegend={false}
              />
              <CustomLegend data={categoryData} />
            </View>
          ) : (
            <Text style={styles.noDataText}>No category data found.</Text>
          )}
        </View>

        {/* 2. Tag Spending (Custom Horizontal Bar List) */}
        <View style={styles.chartContainer}>
          <Text style={styles.chartTitle}>Behavioral Profile</Text>
          {tagEntries.length > 0 ? (
            <HorizontalBarList data={tagEntries} />
          ) : (
            <Text style={styles.noDataText}>No behavioral tags found.</Text>
          )}
        </View>

        {/* 3. Payment Type Chart */}
        <View style={styles.chartContainer}>
          <Text style={styles.chartTitle}>Payment Method</Text>
          {paymentData.length > 0 ? (
            <View>
              <PieChart
                data={paymentData}
                width={SCREEN_WIDTH - 32}
                height={220}
                chartConfig={CHART_CONFIG}
                accessor={"amount"}
                backgroundColor={"transparent"}
                paddingLeft={"15"}
                center={[10, 0]}
                hasLegend={false}
              />
              <CustomLegend data={paymentData} />
            </View>
          ) : (
            <Text style={styles.noDataText}>No payment data found.</Text>
          )}
        </View>

        <View style={{ height: 50 }} />
      </ScrollView>
    );
  };

  return (
    <SafeAreaView style={styles.container}>
      {/* Header with Tabs */}
      <View style={styles.headerContainer}>
        <View style={styles.header}>
          <Text style={styles.title}>Finance Insights</Text>
        </View>
      </View>

      <View style={styles.content}>
        {renderInsights()}
      </View>
    </SafeAreaView>
  );
};

// Helper for colors
const getRandomColor = (index) => {
  const colors = [
    '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', 
    '#FF9F40', '#E7E9ED', '#8AC926', '#1982C4', '#6A4C93'
  ];
  return colors[index % colors.length];
};



const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#121212',
  },
  headerContainer: {
    backgroundColor: '#1E1E1E',
    borderBottomWidth: 1,
    borderBottomColor: '#333',
  },
  header: {
    padding: 20,
    paddingBottom: 10,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#fff',
  },
  tabContainer: {
    flexDirection: 'row',
    paddingHorizontal: 20,
    paddingBottom: 10,
  },
  tab: {
    marginRight: 20,
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderRadius: 20,
  },
  activeTab: {
    backgroundColor: '#333',
  },
  tabText: {
    fontSize: 16,
    color: '#888',
    fontWeight: '600',
  },
  activeTabText: {
    color: '#4A90E2',
  },
  content: {
    flex: 1,
  },
  list: {
    padding: 16,
    paddingBottom: 100,
  },
  scrollContent: {
    padding: 16,
    paddingBottom: 100,
  },
  card: {
    backgroundColor: '#1E1E1E',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#333',
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
  },
  categoryName: {
    fontSize: 18,
    fontWeight: '600',
    color: '#fff',
  },
  saveButton: {
    backgroundColor: '#4A90E2',
    width: 32,
    height: 32,
    borderRadius: 16,
    justifyContent: 'center',
    alignItems: 'center',
  },
  inputsRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  inputGroup: {
    flex: 1,
  },
  label: {
    fontSize: 12,
    color: '#888',
    marginBottom: 4,
  },
  inputWrapper: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#2C2C2C',
    borderRadius: 8,
    paddingHorizontal: 8,
  },
  currencySymbol: {
    color: '#888',
    fontSize: 16,
    marginRight: 4,
  },
  input: {
    flex: 1,
    color: '#fff',
    fontSize: 16,
    paddingVertical: 8,
  },
  divider: {
    width: 1,
    height: 40,
    backgroundColor: '#333',
    marginHorizontal: 16,
  },
  // Insights Styles
  monthPicker: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 20,
    backgroundColor: '#1E1E1E',
    padding: 10,
    borderRadius: 12,
  },
  arrowBtn: {
    padding: 10,
  },
  monthLabel: {
    color: '#fff',
    fontSize: 18,
    fontWeight: 'bold',
    marginHorizontal: 20,
  },
  chartContainer: {
    backgroundColor: '#1E1E1E',
    borderRadius: 12,
    padding: 16,
    marginBottom: 20,
    alignItems: 'center',
  },
  chartTitle: {
    color: '#fff',
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 16,
    alignSelf: 'flex-start',
  },
  noDataText: {
    color: '#888',
    fontStyle: 'italic',
    marginVertical: 20,
  },
  emptyText: {
    color: '#888',
    textAlign: 'center',
    marginTop: 50,
    fontSize: 16,
  },
  // New Chart Styles
  legendContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'center',
    marginTop: 10,
  },
  legendItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginRight: 16,
    marginBottom: 8,
  },
  legendDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    marginRight: 6,
  },
  legendText: {
    color: '#ccc',
    fontSize: 12,
  },
  barListContainer: {
    width: '100%',
  },
  barRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  barLabelContainer: {
    width: 110, 
    paddingRight: 8,
  },
  barLabel: {
    color: '#ccc',
    fontSize: 12,
    textAlign: 'right',
  },
  barWrapper: {
    flex: 1,
    height: 12,
    backgroundColor: '#333',
    borderRadius: 6,
    overflow: 'hidden',
    marginRight: 8,
  },
  barFill: {
    height: '100%',
    borderRadius: 6,
  },
  barValue: {
    color: '#fff',
    fontSize: 12,
    width: 50,
    textAlign: 'right',
  }
});

export default InsightsScreen;

// --- Custom Components ---

export const CustomLegend = ({ data }) => {
  return (
    <View style={styles.legendContainer}>
      {data.map((item, index) => (
        <View key={index} style={styles.legendItem}>
          <View style={[styles.legendDot, { backgroundColor: item.color }]} />
          <Text style={styles.legendText}>{item.name}</Text>
        </View>
      ))}
    </View>
  );
};

const HorizontalBarList = ({ data }) => {
  if (!data || data.length === 0) return null;
  
  const maxValue = Math.max(...data.map(([_, val]) => val));

  return (
    <View style={styles.barListContainer}>
      {data.map(([label, value], index) => {
        const widthPercent = (value / maxValue) * 100;
        return (
          <View key={index} style={styles.barRow}>
            <View style={styles.barLabelContainer}>
              <Text style={styles.barLabel}>{label}</Text>
            </View>
            <View style={styles.barWrapper}>
              <View 
                style={[
                  styles.barFill, 
                  { 
                    width: `${widthPercent}%`,
                    backgroundColor: getRandomColor(index) 
                  }
                ]} 
              />
            </View>
            <Text style={styles.barValue}>₹{value.toFixed(0)}</Text>
          </View>
        );
      })}
    </View>
  );
};

