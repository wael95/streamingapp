import * as React from 'react';
import { Text, View, StyleSheet } from 'react-native';
import { Constants } from 'expo';
import { Container, Content } from 'native-base';

export default class Profile extends React.Component {
  render() {
    return (
      <Container>
        <View style={[styles.container, { backgroundColor: '#cc0000' }]}>
          <Text style={styles.paragraph}>Profile</Text>
        </View>
      </Container>
    );
  }
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingTop: Constants.statusBarHeight,
  },
  paragraph: {
    margin: 24,
    fontSize: 30,
    fontWeight: 'bold',
    textAlign: 'center',
    color: '#ccffff',
  },
});
