import * as React from 'react';
import { Text, View, Image, TouchableOpacity, Dimensions } from 'react-native';

export default class FriendSream extends React.Component {
  render() {
    return (
      <TouchableOpacity
        style={{
          height: 300,
          width: this.props.width / 2.1,
          marginTop: 2,
          marginLeft: 2,
          overflow: 'hidden',
        }}>
        <View style={{ flex: 1 }}>
          <Image
            style={{
              flex: 1,
              height: null,
              width: null,
              resizeMode: 'cover',
            }}
            source={this.props.source1}
          />
        </View>
        {this.props.source2 ? <View style={{ flex: 1 }}>
          <Image
            style={{
              flex: 1,
              height: null,
              width: null,
              resizeMode: 'cover',
            }}
            source={this.props.source2}
          />
        </View> : <View/>}
      </TouchableOpacity>
    );
  }
}
