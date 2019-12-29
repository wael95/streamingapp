import * as React from 'react';
import { Text, View, StyleSheet } from 'react-native';
import { Constants } from 'expo';
import { Button, Container } from 'native-base'; // Version can be specified in package.json
import Swiper from 'react-native-swiper'; // Version can be specified in package.json

import Camera from './components/Camera';
import Feeds from './components/Feeds';
import Messages from './components/Messages';
import Profile from './components/Profile';
export default class App extends React.Component {
  constructor() {
    super();
    this.state = { OuterScrollEnabled: true };
  }
  verticalScroll = index => {
    if (index !== 1) {
      this.setState({ OuterScrollEnabled: false });
    } else {
      this.setState({ OuterScrollEnabled: true });
    }
  };
  render() {
    return (
      <Container>
        <Swiper loop={false} showsPagination={false} index={1}>
          <Messages />
          <View style={{ flex: 1 }}>
            <Camera />
          </View>
          <Feeds />
        </Swiper>
      </Container>
    );
  }
}
